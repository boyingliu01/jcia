"""SkyWalking APM 数据适配器实现.

基于 SkyWalking APM 数据的测试推荐和性能分析适配器。
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_OAP_SERVER = "http://localhost:12800"
DEFAULT_TIME_RANGE_DAYS = 7


class SkyWalkingAdapter:
    """SkyWalking APM 数据适配器.

    基于 SkyWalking OAP Server 的 GraphQL API 提供：
    - 测试用例推荐
    - 性能瓶颈分析
    - 异常追踪
    """

    def __init__(
        self,
        oap_server: str = DEFAULT_OAP_SERVER,
        api_token: str | None = None,
        timeout: int = 30,
    ) -> None:
        """初始化适配器.

        Args:
            oap_server: OAP Server 地址
            api_token: API 访问令牌（可选）
            timeout: 请求超时时间（秒）
        """
        self._oap_server = oap_server.rstrip("/")
        self._token = api_token
        self._timeout = timeout
        self._graphql_endpoint = f"{self._oap_server}/graphql"

        logger.info(f"SkyWalkingAdapter initialized: {self._graphql_endpoint}")

    def recommend_tests(
        self, changed_methods: list[str], time_range: int = 7
    ) -> list[dict[str, Any]]:
        """基于 APM 数据推荐测试.

        Args:
            changed_methods: 变更的方法列表
            time_range: 时间范围（天）

        Returns:
            List[dict]: 测试推荐列表
        """
        logger.info(f"Generating test recommendations for {len(changed_methods)} changes")

        # 1. 查找相关服务 endpoint
        endpoints = self._find_related_endpoints(changed_methods)

        if not endpoints:
            logger.warning("No related endpoints found")
            return []

        # 2. 分析 endpoint 的调用频率和错误率
        endpoint_stats = self._analyze_endpoint_stats(endpoints, time_range)

        # 3. 生成测试推荐
        recommendations = []

        for stat in endpoint_stats:
            if stat["error_rate"] > 0.01 or stat["slow_calls"] > 10:
                recommendation = {
                    "endpoint": stat["endpoint"],
                    "test_priority": "HIGH",
                    "reason": (
                        f"错误率 {stat['error_rate']:.2%} "
                        f"或慢调用 {stat['slow_calls']} 次"
                    ),
                    "suggested_tests": self._suggest_tests_for_endpoint(stat),
                    "metrics": {
                        "sla": stat["sla"],
                        "throughput": stat["throughput"],
                        "response_time_p95": stat.get("response_time_p95", 0),
                        "response_time_p99": stat.get("response_time_p99", 0),
                    },
                }

                recommendations.append(recommendation)

        logger.info(f"Generated {len(recommendations)} test recommendations")

        return recommendations

    def _find_related_endpoints(self, methods: list[str]) -> list[str]:
        """查找相关 endpoint.

        Args:
            methods: 方法列表

        Returns:
            List[str]: 相关 endpoint ID 列表
        """
        query = """
        query($endpoints: [String!]!) {
            endpoints: searchEndpoint(keyword: $endpoints) {
                key: id
                label: name
                serviceId
                serviceName
                type
            }
        }
        """

        # 将方法名转换为可能的 endpoint
        endpoint_keywords = []
        for method in methods:
            # 提取类名和方法名
            parts = method.split(".")
            if len(parts) >= 2:
                endpoint_keywords.append(parts[-2])  # 类名
                endpoint_keywords.append(parts[-1])  # 方法名

        try:
            response = self._execute_graphql(query, {"endpoints": endpoint_keywords})
            endpoints_data = response.get("endpoints", [])

            endpoint_ids = [ep["key"] for ep in endpoints_data]

            logger.info(f"Found {len(endpoint_ids)} related endpoints")

            return endpoint_ids

        except Exception as e:
            logger.error(f"Failed to find related endpoints: {e}")
            return []

    def _analyze_endpoint_stats(
        self, endpoint_ids: list[str], time_range: int
    ) -> list[dict[str, Any]]:
        """分析 endpoint 统计信息.

        Args:
            endpoint_ids: endpoint ID 列表
            time_range: 时间范围（天）

        Returns:
            List[dict]: endpoint 统计列表
        """
        query = """
        query($ids: [ID!]!, $start: Long!, $end: Long!) {
            stats: queryEndpointStats(duration: { start: $start, end: $end }) {
                endpointId
                sla
                throughput
                responseTime: latency {
                    avg
                    p95
                    p99
                }
                errorRate: errorRate {
                    value
                }
            }
        }
        """

        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (time_range * 24 * 3600 * 1000)

        try:
            response = self._execute_graphql(
                query,
                {
                    "ids": endpoint_ids,
                    "start": start_time,
                    "end": end_time,
                },
            )

            stats_data = response.get("stats", [])

            return self._process_endpoint_stats(stats_data, endpoint_ids)

        except Exception as e:
            logger.error(f"Failed to analyze endpoint stats: {e}")
            return []

    def _process_endpoint_stats(
        self, stats_data: list, endpoint_ids: list[str]
    ) -> list[dict[str, Any]]:
        """处理 endpoint 统计数据.

        Args:
            stats_data: SkyWalking 统计数据
            endpoint_ids: endpoint ID 列表

        Returns:
            List[dict]: 处理后的统计信息
        """
        # 构建endpoint ID到名称的映射
        endpoint_map = {}
        query = """
        query($ids: [ID!]!) {
            endpoints: searchEndpoint(keyword: $ids) {
                key: id
                label: name
            }
        }
        """

        try:
            response = self._execute_graphql(query, {"ids": endpoint_ids})
            endpoints = response.get("endpoints", [])
            endpoint_map = {ep["key"]: ep["label"] for ep in endpoints}
        except Exception:
            endpoint_map = {}

        # 处理统计数据
        processed = []

        for stat in stats_data:
            endpoint_id = stat.get("endpointId", "")

            # 计算慢调用次数（假设 p95 > 1000ms 为慢）
            response_time = stat.get("responseTime", {})
            p95 = response_time.get("p95", 0)
            p99 = response_time.get("p99", 0)

            slow_threshold = 1000  # 1秒
            slow_calls = 0
            if p95 > slow_threshold:
                slow_calls = int(stat.get("throughput", 0) * 0.1)  # 估算

            # 获取错误率
            error_rate_value = stat.get("errorRate", {}).get("value", 0)

            processed.append(
                {
                    "endpoint": endpoint_map.get(endpoint_id, endpoint_id),
                    "endpoint_id": endpoint_id,
                    "sla": stat.get("sla", 0),
                    "throughput": stat.get("throughput", 0),
                    "response_time_avg": response_time.get("avg", 0),
                    "response_time_p95": p95,
                    "response_time_p99": p99,
                    "error_rate": error_rate_value,
                    "slow_calls": slow_calls,
                }
            )

        return processed

    def _suggest_tests_for_endpoint(self, endpoint_stat: dict) -> list[str]:
        """为 endpoint 建议测试.

        Args:
            endpoint_stat: endpoint 统计信息

        Returns:
            List[str]: 测试建议列表
        """
        endpoint = endpoint_stat["endpoint"]
        suggestions = []

        # 基于endpoint名称生成测试建议
        parts = endpoint.split(".")

        if len(parts) >= 2:
            service_name = parts[-2]
            method_name = parts[-1]

            # 正常流程测试
            suggestions.append(
                f"测试 {service_name}.{method_name} 的正常调用流程"
            )

            # 错误处理测试
            suggestions.append(
                f"测试 {service_name}.{method_name} 的异常情况处理"
            )

        # 性能测试
        if endpoint_stat.get("response_time_p95", 0) > 500:
            suggestions.append(
                f"对 {endpoint} 进行性能测试，响应时间应 < 500ms"
            )

        # 并发测试
        if endpoint_stat.get("throughput", 0) > 100:
            suggestions.append(
                f"对 {endpoint} 进行并发测试，验证高负载下的稳定性"
            )

        return suggestions

    def analyze_exceptions(
        self, service_name: str, time_range: int = 7
    ) -> list[dict[str, Any]]:
        """分析服务异常.

        Args:
            service_name: 服务名
            time_range: 时间范围（天）

        Returns:
            List[dict]: 异常列表
        """
        query = """
        query($serviceId: ID!, $start: Long!, $end: Long!) {
            exceptions: queryLogs(condition: {
                keyword: "ERROR"
                duration: { start: $start, end: $end }
                serviceName: $serviceId
            }) {
                logs {
                    timestamp
                    serviceId
                    endpointId
                    traceId
                    contentType: exception
                    content: exception {
                        exceptionType
                        message
                        stackTrace {
                            className
                            methodName
                            lineNumber
                        }
                    }
                }
            }
        }
        """

        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (time_range * 24 * 3600 * 1000)

        try:
            response = self._execute_graphql(
                query,
                {
                    "serviceId": service_name,
                    "start": start_time,
                    "end": end_time,
                },
            )

            exceptions_data = response.get("exceptions", {}).get("logs", [])

            return self._process_exception_logs(exceptions_data)

        except Exception as e:
            logger.error(f"Failed to analyze exceptions: {e}")
            return []

    def _process_exception_logs(self, logs: list) -> list[dict[str, Any]]:
        """处理异常日志.

        Args:
            logs: 异常日志列表

        Returns:
            List[dict]: 处理后的异常列表
        """
        exceptions = []

        for log in logs:
            exception_info = log.get("content", {}).get("exception", {})

            exception = {
                "timestamp": log.get("timestamp", 0),
                "service_id": log.get("serviceId", ""),
                "endpoint_id": log.get("endpointId", ""),
                "trace_id": log.get("traceId", ""),
                "exception_type": exception_info.get("exceptionType", ""),
                "message": exception_info.get("message", ""),
                "stack_trace": self._format_stack_trace(
                    exception_info.get("stackTrace", [])
                ),
            }

            exceptions.append(exception)

        logger.info(f"Found {len(exceptions)} exceptions")

        return exceptions

    def _format_stack_trace(self, stack_trace: list) -> str:
        """格式化堆栈跟踪.

        Args:
            stack_trace: 堆栈跟踪列表

        Returns:
            str: 格式化的堆栈跟踪
        """
        if not stack_trace:
            return ""

        lines = []
        for frame in stack_trace:
            line = (
                f"  at {frame.get('className', '')}."
                f"{frame.get('methodName', '')}("
                f"Line {frame.get('lineNumber', '')}"
            )
            lines.append(line)

        return "\n".join(lines)

    def get_service_health(self, service_names: list[str]) -> dict[str, Any]:
        """获取服务健康状态.

        Args:
            service_names: 服务名列表

        Returns:
            Dict[str, Any]: 服务健康状态
        """
        query = """
        query {
            services {
                key: id
                label: name
                metrics {
                    label: service_cpm
                    value: avg
                }
                healthCheck {
                    status
                    message
                    timestamp
                }
            }
        }
        """

        try:
            response = self._execute_graphql(query, {})

            services_data = response.get("services", [])

            # 过滤指定服务
            filtered_services = [
                svc
                for svc in services_data
                if svc["label"] in service_names
            ]

            return {"services": filtered_services}

        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {"services": []}

    def analyze_performance_trends(
        self, service_name: str, time_range: int = 30
    ) -> dict[str, Any]:
        """分析性能趋势.

        Args:
            service_name: 服务名
            time_range: 时间范围（天）

        Returns:
            Dict[str, Any]: 性能趋势数据
        """
        query = """
        query($name: String!, $start: Long!, $end: Long!) {
            linear: queryMetrics(condition: {
                name: $name
                duration: { start: $start, end: $end }
            }) {
                id: id
                name: name
                values {
                    id: id
                    instanceId: id
                    values {
                        value: value
                    }
                }
            }
        }
        """

        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (time_range * 24 * 3600 * 1000)

        try:
            response = self._execute_graphql(
                query,
                {
                    "name": service_name,
                    "start": start_time,
                    "end": end_time,
                },
            )

            return {
                "service_name": service_name,
                "metrics": response.get("linear", {}).get("values", []),
                "time_range_days": time_range,
            }

        except Exception as e:
            logger.error(f"Failed to analyze performance trends: {e}")
            return {"service_name": service_name, "metrics": []}

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

    def export_test_recommendations(
        self, recommendations: list[dict], output_file: Path
    ) -> None:
        """导出测试推荐到文件.

        Args:
            recommendations: 测试推荐列表
            output_file: 输出文件路径
        """
        import json

        data = {
            "generated_at": datetime.now().isoformat(),
            "total_recommendations": len(recommendations),
            "recommendations": recommendations,
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Test recommendations exported to {output_file}")
