"""SkyWalking 调用链分析器适配器实现.

基于 SkyWalking 分布式追踪数据的动态调用链分析器。
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass, field as dc_field

from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainAnalyzer,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_OAP_SERVER = "http://localhost:12800"
DEFAULT_TIME_RANGE_DAYS = 7


@dataclass
class DubboCall:
    """Dubbo 调用记录."""

    interface: str
    method: str
    version: str | None = None
    group: str | None = None
    consumer: str = ""
    provider: str = ""


@dataclass
class ServiceEndpoint:
    """服务端点."""

    service_id: str
    service_name: str
    endpoint_name: str
    type: str
    tags: dict = dc_field(default_factory=dict)


class SkyWalkingCallChainAdapter(CallChainAnalyzer):
    """SkyWalking 调用链分析器.

    基于 SkyWalking OAP Server 的 GraphQL API 构建动态调用链：
    - 支持跨服务调用分析
    - 基于实际运行时的调用关系
    - 识别远程调用（Dubbo、gRPC、REST）
    """

    def __init__(
        self,
        oap_server: str = DEFAULT_OAP_SERVER,
        api_token: str | None = None,
        time_range: int = DEFAULT_TIME_RANGE_DAYS,
        timeout: int = 30,
    ) -> None:
        """初始化分析器.

        Args:
            oap_server: OAP Server 地址
            api_token: API 访问令牌（可选）
            time_range: 追踪数据时间范围（天）
            timeout: 请求超时时间（秒）
        """
        self._oap_server = oap_server.rstrip("/")
        self._token = api_token
        self._time_range = time_range
        self._timeout = timeout
        self._graphql_endpoint = f"{self._oap_server}/graphql"

        logger.info(
            f"SkyWalkingCallChainAdapter initialized: {self._graphql_endpoint}"
        )

    @property
    def analyzer_type(self) -> AnalyzerType:
        """返回分析器类型."""
        return AnalyzerType.DYNAMIC

    @property
    def supports_cross_service(self) -> bool:
        """是否支持跨服务分析."""
        return True

    def analyze_upstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析上游调用者（基于实际追踪数据）.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            CallChainGraph: 上游调用链图
        """
        logger.debug(f"Analyzing upstream with SkyWalking for method: {method}")

        service, endpoint = self._parse_method_to_endpoint(method)

        query = """
        query($serviceName: String!, $endpointName: String!, $start: Long!, $end: Long!) {
            getTrace: queryBasicTraces(condition: {
                serviceName: $serviceName
                endpointName: $endpointName
                queryDuration: { start: $start, end: $end }
                traceState: ALL
            }) {
                traces {
                    segments {
                        serviceId
                        serviceCode
                        spans {
                            spanId
                            parentSpanId
                            peer
                            operationName
                            type
                            component
                            startTime
                            endTime
                            tags {
                                key
                                value
                            }
                        }
                    }
                }
            }
        }
        """

        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (self._time_range * 24 * 3600 * 1000)

        try:
            response = self._execute_graphql(
                query,
                {
                    "serviceName": service,
                    "endpointName": endpoint,
                    "start": start_time,
                    "end": end_time,
                },
            )

            traces_data = response.get("getTrace", {})
            return self._build_upstream_graph(traces_data, method, max_depth)

        except Exception as e:
            logger.error(f"Failed to analyze upstream: {e}")
            return self._create_empty_graph(method, max_depth)

    def analyze_downstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析下游被调用者（基于实际追踪数据）.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            CallChainGraph: 下游调用链图
        """
        logger.debug(f"Analyzing downstream with SkyWalking for method: {method}")

        service, endpoint = self._parse_method_to_endpoint(method)

        query = """
        query($serviceName: String!, $endpointName: String!, $start: Long!, $end: Long!) {
            getTrace: queryBasicTraces(condition: {
                serviceName: $serviceName
                endpointName: $endpointName
                queryDuration: { start: $start, end: $end }
                traceState: ALL
            }) {
                traces {
                    segments {
                        serviceId
                        serviceCode
                        spans {
                            spanId
                            parentSpanId
                            peer
                            operationName
                            type
                            component
                            startTime
                            endTime
                            tags {
                                key
                                value
                            }
                        }
                    }
                }
            }
        }
        """

        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (self._time_range * 24 * 3600 * 1000)

        try:
            response = self._execute_graphql(
                query,
                {
                    "serviceName": service,
                    "endpointName": endpoint,
                    "start": start_time,
                    "end": end_time,
                },
            )

            traces_data = response.get("getTrace", {})
            return self._build_downstream_graph(traces_data, method, max_depth)

        except Exception as e:
            logger.error(f"Failed to analyze downstream: {e}")
            return self._create_empty_graph(method, max_depth)

    def analyze_both_directions(
        self, method: str, max_depth: int = 10
    ) -> tuple[CallChainGraph, CallChainGraph]:
        """同时分析上下游.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            tuple[CallChainGraph, CallChainGraph]: (上游图, 下游图)
        """
        upstream = self.analyze_upstream(method, max_depth)
        downstream = self.analyze_downstream(method, max_depth)
        return upstream, downstream

    def build_full_graph(self) -> CallChainGraph:
        """构建完整的调用链图.

        Returns:
            CallChainGraph: 完整调用链图
        """
        query = """
        query {
            services {
                key: id
                label: name
            }
            topology {
                id
                name
                type
                components {
                    id
                    name
                    type
                }
                links {
                    sourceId
                    targetId
                }
            }
        }
        """

        try:
            response = self._execute_graphql(query, {})

            services = response.get("services", [])
            topology = response.get("topology", {})

            return self._build_full_graph_from_topology(topology)

        except Exception as e:
            logger.error(f"Failed to build full graph: {e}")
            return self._create_empty_graph("root", 10)

    def _parse_method_to_endpoint(self, method: str) -> tuple[str, str]:
        """将方法全限定名转换为 SkyWalking endpoint 格式.

        Args:
            method: 方法全限定名

        Returns:
            Tuple[str, str]: (服务名, 端点名)
        """
        # com.example.UserService.getById -> UserService, getById
        parts = method.split(".")
        if len(parts) >= 2:
            service_name = parts[-2]
            endpoint_name = parts[-1]
            return service_name, endpoint_name

        return method, method

    def _execute_graphql(self, query: str, variables: dict) -> dict:
        """执行 GraphQL 查询.

        Args:
            query: GraphQL 查询字符串
            variables: 查询变量

        Returns:
            Dict[str, Any]: 查询结果

        Raises:
            RuntimeError: 查询失败
        """
        import requests

        headers = {
            "Content-Type": "application/json",
        }

        if self._token:
            headers["SW-TOKEN"] = self._token

        payload = {
            "query": query,
            "variables": variables,
        }

        try:
            response = requests.post(
                self._graphql_endpoint,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )

            response.raise_for_status()

            data = response.json()

            if "errors" in data:
                error_msg = "; ".join(
                    err.get("message", "Unknown error") for err in data["errors"]
                )
                raise RuntimeError(f"GraphQL error: {error_msg}")

            return data.get("data", {})

        except requests.exceptions.RequestException as e:
            logger.error(f"GraphQL request failed: {e}")
            raise RuntimeError(f"Failed to execute GraphQL query: {e}") from e

    def _build_upstream_graph(
        self, traces_data: dict, root_method: str, max_depth: int
    ) -> CallChainGraph:
        """从追踪数据构建上游调用图.

        Args:
            traces_data: SkyWalking 追踪数据
            root_method: 根方法名
            max_depth: 最大深度

        Returns:
            CallChainGraph: 上游调用图
        """
        class_name, method_name = self._parse_method_to_endpoint(root_method)

        root = CallChainNode(
            class_name=class_name,
            method_name=method_name,
            signature=None,
        )

        traces = traces_data.get("traces", [])
        total_nodes = 1

        # 遍历所有追踪
        for trace in traces:
            segments = trace.get("segments", [])

            for segment in segments:
                service_name = segment.get("serviceCode", "")
                spans = segment.get("spans", [])

                for span in spans:
                    span_type = span.get("type", "")
                    parent_span_id = span.get("parentSpanId")

                    # 只处理上游调用（有父节点的）
                    if parent_span_id and span_type != "Entry":
                        peer = span.get("peer", "")
                        operation_name = span.get("operationName", "")

                        # 识别调用类型
                        call_type, service_info = self._identify_call_type_from_span(span)

                        node = CallChainNode(
                            class_name=peer,
                            method_name=operation_name,
                            signature=None,
                            service=service_info,
                            children=[],
                        )

                        node.metadata = {
                            "call_type": call_type,
                            "component": span.get("component", ""),
                            "span_id": span.get("spanId"),
                        }

                        # 添加到上游调用链
                        root.children.append(node)
                        total_nodes += 1

                        # 递归添加上游调用
                        self._add_upstream_nodes(
                            root, node, spans, parent_span_id, depth=1, max_depth=max_depth
                        )

        return CallChainGraph(
            root=root,
            direction=CallChainDirection.UPSTREAM,
            max_depth=max_depth,
            total_nodes=total_nodes,
        )

    def _add_upstream_nodes(
        self,
        root: CallChainNode,
        current: CallChainNode,
        spans: list,
        parent_span_id: str,
        depth: int,
        max_depth: int,
    ) -> None:
        """递归添加上游节点.

        Args:
            root: 根节点
            current: 当前节点
            spans: 所有 span
            parent_span_id: 父 span ID
            depth: 当前深度
            max_depth: 最大深度
        """
        if depth >= max_depth:
            return

        for span in spans:
            if span.get("parentSpanId") == parent_span_id:
                # 创建子节点
                peer = span.get("peer", "")
                operation_name = span.get("operationName", "")

                child = CallChainNode(
                    class_name=peer,
                    method_name=operation_name,
                    signature=None,
                    service=peer,
                )

                # 识别调用类型
                call_type, service_info = self._identify_call_type_from_span(span)

                child.metadata = {
                    "call_type": call_type,
                    "component": span.get("component", ""),
                    "span_id": span.get("spanId"),
                }

                current.children.append(child)

                # 递归处理
                self._add_upstream_nodes(
                    root, child, spans, span.get("spanId"), depth + 1, max_depth
                )

    def _build_downstream_graph(
        self, traces_data: dict, root_method: str, max_depth: int
    ) -> CallChainGraph:
        """从追踪数据构建下游调用图.

        Args:
            traces_data: SkyWalking 追踪数据
            root_method: 根方法名
            max_depth: 最大深度

        Returns:
            CallChainGraph: 下游调用图
        """
        class_name, method_name = self._parse_method_to_endpoint(root_method)

        root = CallChainNode(
            class_name=class_name,
            method_name=method_name,
            signature=None,
        )

        traces = traces_data.get("traces", [])
        total_nodes = 1

        # 遍历所有追踪
        for trace in traces:
            segments = trace.get("segments", [])

            for segment in segments:
                service_name = segment.get("serviceCode", "")
                spans = segment.get("spans", [])

                for span in spans:
                    span_type = span.get("type", "")

                    # 只处理下游调用（Exit 类型的）
                    if span_type == "Exit":
                        peer = span.get("peer", "")
                        operation_name = span.get("operationName", "")

                        # 识别调用类型
                        call_type, service_info = self._identify_call_type_from_span(span)

                        node = CallChainNode(
                            class_name=peer,
                            method_name=operation_name,
                            signature=None,
                            service=service_info,
                            children=[],
                        )

                        node.metadata = {
                            "call_type": call_type,
                            "component": span.get("component", ""),
                            "span_id": span.get("spanId"),
                        }

                        # 添加到下游调用链
                        root.children.append(node)
                        total_nodes += 1

        return CallChainGraph(
            root=root,
            direction=CallChainDirection.DOWNSTREAM,
            max_depth=max_depth,
            total_nodes=total_nodes,
        )

    def _build_full_graph_from_topology(self, topology: dict) -> CallChainGraph:
        """从拓扑数据构建完整调用图.

        Args:
            topology: 服务拓扑数据

        Returns:
            CallChainGraph: 完整调用图
        """
        # 创建虚拟根节点
        root = CallChainNode(class_name="root", method_name="root", signature=None)

        # 遍历所有链接
        links = topology.get("links", [])

        for link in links:
            source_id = link.get("sourceId")
            target_id = link.get("targetId")

            # 创建节点
            node = CallChainNode(
                class_name=target_id,
                method_name=target_id,
                signature=None,
                children=[],
            )

            node.metadata = {
                "link_type": "service_dependency",
                "source": source_id,
            }

            root.children.append(node)

        return CallChainGraph(
            root=root,
            direction=CallChainDirection.BOTH,
            max_depth=10,
            total_nodes=len(links),
        )

    def _identify_call_type_from_span(self, span: dict) -> tuple[str, str]:
        """从 span 识别调用类型.

        Args:
            span: SkyWalking span 数据

        Returns:
            Tuple[str, str]: (调用类型, 服务信息)
        """
        tags = span.get("tags", [])
        component = span.get("component", "")
        peer = span.get("peer", "")

        # 构建标签字典
        tag_dict = {tag.get("key"): tag.get("value") for tag in tags}

        # 检查 Dubbo
        if component == "Dubbo" or "dubbo.interface" in tag_dict:
            interface = tag_dict.get("dubbo.interface", "")
            return ("dubbo", interface)

        # 检查 gRPC
        if component == "gRPC" or "rpc" in tag_dict.get("url", "").lower():
            return ("grpc", peer)

        # 检查 REST
        if "http" in tag_dict.get("protocol", "").lower() or component in ["Spring", "Tomcat"]:
            url = tag_dict.get("url", "")
            return ("rest", url)

        # 检查数据库
        if tag_dict.get("db.type"):
            db_type = tag_dict.get("db.type")
            return ("database", db_type)

        # 检查消息队列
        if tag_dict.get("mq.type"):
            mq_type = tag_dict.get("mq.type")
            return ("message_queue", mq_type)

        # 默认为本地调用
        return ("local", peer)

    def _identify_dubbo_calls(self, traces_data: dict) -> dict[str, DubboCall]:
        """识别 Dubbo 调用.

        Args:
            traces_data: SkyWalking 追踪数据

        Returns:
            Dict[str, DubboCall]: Dubbo 调用记录
        """
        dubbo_calls = {}

        traces = traces_data.get("traces", [])

        for trace in traces:
            segments = trace.get("segments", [])

            for segment in segments:
                service_name = segment.get("serviceCode", "")
                spans = segment.get("spans", [])

                for span in spans:
                    if span.get("component") == "Dubbo":
                        tags = span.get("tags", [])
                        tag_dict = {tag.get("key"): tag.get("value") for tag in tags}

                        # 解析 Dubbo 调用信息
                        dubbo_call = DubboCall(
                            interface=tag_dict.get("dubbo.interface", ""),
                            method=tag_dict.get("dubbo.method", ""),
                            version=tag_dict.get("dubbo.version"),
                            group=tag_dict.get("dubbo.group"),
                            consumer=service_name,
                            provider=span.get("peer", "unknown"),
                        )

                        dubbo_calls[span.get("spanId")] = dubbo_call

        return dubbo_calls

    def get_service_topology(self) -> dict[str, Any]:
        """获取服务拓扑.

        Returns:
            Dict[str, Any]: 服务拓扑数据
        """
        query = """
        query {
            services {
                key: id
                label: name
            }
            topology {
                id
                name
                type
                components {
                    id
                    name
                    type
                }
                links {
                    sourceId
                    targetId
                }
            }
        }
        """

        try:
            response = self._execute_graphql(query, {})

            return {
                "services": response.get("services", []),
                "topology": response.get("topology", {}),
            }

        except Exception as e:
            logger.error(f"Failed to get service topology: {e}")
            return {"services": [], "topology": {}}

    def _create_empty_graph(self, method: str, max_depth: int) -> CallChainGraph:
        """创建空调用链图.

        Args:
            method: 方法名
            max_depth: 最大深度

        Returns:
            CallChainGraph: 空的调用链图
        """
        class_name, method_name = self._parse_method_to_endpoint(method)

        root = CallChainNode(
            class_name=class_name,
            method_name=method_name,
            signature=None,
        )

        return CallChainGraph(
            root=root,
            direction=CallChainDirection.BOTH,
            max_depth=max_depth,
            total_nodes=1,
        )
