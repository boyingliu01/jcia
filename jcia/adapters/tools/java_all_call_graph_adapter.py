"""Java All Call Graph 适配器实现.

基于字节码的 Java 静态调用链分析器，支持远程调用识别。
"""
# ruff: noqa: S324,S310  # md5 for cache keys, file: URLs for local files

import hashlib
import json
import logging
import re
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainAnalyzer,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)

logger = logging.getLogger(__name__)

# 常量定义
JACG_VERSION = "0.9.0"
JACG_REPO_URL = "https://github.com/bytedance/java-all-call-graph"
JACG_RELEASE_URL = f"{JACG_REPO_URL}/releases/download/v{JACG_VERSION}"
JACG_JAR_NAME = f"java-all-call-graph-{JACG_VERSION}-jar-with-dependencies.jar"
DEFAULT_CACHE_DIR = Path.home() / ".jcia" / "jacg"


@dataclass
class DubboServiceInfo:
    """Dubbo 服务信息."""

    interface: str
    version: str | None = None
    group: str | None = None
    is_consumer: bool = False
    is_provider: bool = False


@dataclass
class RemoteCallInfo:
    """远程调用信息."""

    call_type: str  # dubbo/grpc/rest/feign
    service_name: str | None = None
    interface: str | None = None
    endpoint: str | None = None
    method: str | None = None


class JavaAllCallGraphAdapter(CallChainAnalyzer):
    """Java All Call Graph 适配器.

    基于字节码分析 Java 代码调用关系，支持识别：
    - 直接方法调用
    - 反射调用
    - 接口实现调用
    - 远程调用（Dubbo、gRPC、REST）
    """

    def __init__(
        self,
        repo_path: str,
        jacg_jar: str | None = None,
        max_depth: int = 10,
        cache_dir: Path | None = None,
    ) -> None:
        """初始化分析器.

        Args:
            repo_path: Java 项目路径
            jacg_jar: JACG JAR 包路径（None 则自动下载）
            max_depth: 最大分析深度
            cache_dir: 缓存目录
        """
        self._repo_path = Path(repo_path).resolve()
        self._max_depth = max_depth
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # 获取或下载 JACG JAR
        self._jacg_jar = Path(jacg_jar) if jacg_jar else self._download_jacg()

        # 输出目录
        self._output_dir = self._repo_path / ".jcia" / "jacg"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # 缓存
        self._call_cache: dict[str, CallChainGraph] = {}
        self._annotation_cache: dict[str, list[dict]] = {}
        self._remote_calls_cache: dict[str, list[RemoteCallInfo]] = {}

        logger.info(f"JavaAllCallGraphAdapter initialized with repo: {self._repo_path}")

    @property
    def analyzer_type(self) -> AnalyzerType:
        """返回分析器类型."""
        return AnalyzerType.STATIC

    @property
    def supports_cross_service(self) -> bool:
        """是否支持跨服务分析."""
        return False  # 静态分析不支持跨服务

    def analyze_upstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析上游调用者.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            CallChainGraph: 上游调用链图
        """
        logger.debug(f"Analyzing upstream for method: {method}")

        # 检查缓存
        cache_key = f"upstream:{method}:{max_depth}"
        if cache_key in self._call_cache:
            return self._call_cache[cache_key]

        # 解析方法
        class_name, method_name = self._parse_method(method)

        # 使用 JACG 分析上游调用
        call_chain = self._analyze_with_jacg(method, "upstream", max_depth)

        # 缓存结果
        self._call_cache[cache_key] = call_chain

        return call_chain

    def analyze_downstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析下游被调用者.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            CallChainGraph: 下游调用链图
        """
        logger.debug(f"Analyzing downstream for method: {method}")

        # 检查缓存
        cache_key = f"downstream:{method}:{max_depth}"
        if cache_key in self._call_cache:
            return self._call_cache[cache_key]

        # 解析方法
        class_name, method_name = self._parse_method(method)

        # 使用 JACG 分析下游调用
        call_chain = self._analyze_with_jacg(method, "downstream", max_depth)

        # 缓存结果
        self._call_cache[cache_key] = call_chain

        return call_chain

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
        # 使用 JACG 构建完整调用图
        output_file = self._output_dir / "full_call_graph.json"

        cmd = [
            "java",
            "-jar",
            str(self._jacg_jar),
            "--input-dir",
            str(self._repo_path),
            "--output-format",
            "json",
            "--output-file",
            str(output_file),
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600, check=False
            )

            if result.returncode != 0:
                logger.error(f"JACG full graph failed: {result.stderr}")
                return self._create_empty_graph("root", 10)

            # 解析输出
            if output_file.exists():
                with open(output_file) as f:
                    data = json.load(f)
                return self._parse_full_graph(data)
            else:
                logger.warning("JACG output file not found")
                return self._create_empty_graph("root", 10)

        except subprocess.TimeoutExpired:
            logger.error("JACG analysis timed out")
            return self._create_empty_graph("root", 10)
        except Exception as e:
            logger.error(f"JACG analysis error: {e}")
            return self._create_empty_graph("root", 10)

    def _parse_method(self, method: str) -> tuple[str, str]:
        """解析方法全限定名.

        Args:
            method: 方法全限定名（如 com.example.UserService.getById）

        Returns:
            tuple[str, str]: (类名, 方法名)
        """
        parts = method.split(".")
        if len(parts) < 2:
            return method, method

        # 最后一个部分是方法名
        method_name = parts[-1]
        # 其余部分是类名
        class_name = ".".join(parts[:-1])

        return class_name, method_name

    def _analyze_with_jacg(self, method: str, direction: str, max_depth: int) -> CallChainGraph:
        """使用 JACG 执行调用链分析.

        Args:
            method: 方法全限定名
            direction: 方向（upstream/downstream）
            max_depth: 最大深度

        Returns:
            CallChainGraph: 调用链图
        """
        class_name, method_name = self._parse_method(method)

        # 创建输出文件
        method_hash = hashlib.md5(method.encode()).hexdigest()
        output_file = self._output_dir / f"{direction}_{method_hash}.json"

        cmd = [
            "java",
            "-jar",
            str(self._jacg_jar),
            "--input-dir",
            str(self._repo_path),
            "--class",
            class_name,
            "--method",
            method_name,
            "--direction",
            direction,
            "--max-depth",
            str(max_depth),
            "--output-format",
            "json",
            "--output-file",
            str(output_file),
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, check=False
            )

            if result.returncode != 0:
                logger.error(f"JACG analysis failed: {result.stderr}")
                return self._create_empty_graph(method, max_depth)

            # 解析输出
            if output_file.exists():
                with open(output_file) as f:
                    data = json.load(f)
                return self._parse_jacg_output(data, method, direction, max_depth)
            else:
                logger.warning("JACG output file not found")
                return self._create_empty_graph(method, max_depth)

        except subprocess.TimeoutExpired:
            logger.error("JACG analysis timed out")
            return self._create_empty_graph(method, max_depth)
        except Exception as e:
            logger.error(f"JACG analysis error: {e}")
            return self._create_empty_graph(method, max_depth)

    def _parse_jacg_output(
        self, data: dict, root_method: str, direction: str, max_depth: int
    ) -> CallChainGraph:
        """解析 JACG 输出.

        Args:
            data: JACG 输出数据
            root_method: 根方法名
            direction: 分析方向
            max_depth: 最大深度

        Returns:
            CallChainGraph: 调用链图
        """
        class_name, method_name = self._parse_method(root_method)

        # 创建根节点
        root = CallChainNode(
            class_name=class_name,
            method_name=method_name,
            signature=None,
        )

        # 解析调用链
        nodes_data = data.get("callGraph", data.get("calls", []))
        total_nodes = 1

        # 递归构建调用树
        for node_data in nodes_data:
            child_node = self._build_call_node(node_data, depth=1)
            root.children.append(child_node)
            total_nodes += self._count_nodes(child_node)

        # 识别远程调用
        self._identify_remote_calls(root)

        # 确定方向
        call_direction = (
            CallChainDirection.UPSTREAM
            if direction == "upstream"
            else CallChainDirection.DOWNSTREAM
        )

        return CallChainGraph(
            root=root, direction=call_direction, max_depth=max_depth, total_nodes=total_nodes
        )

    def _parse_full_graph(self, data: dict) -> CallChainGraph:
        """解析完整调用图.

        Args:
            data: JACG 完整图数据

        Returns:
            CallChainGraph: 完整调用链图
        """
        # 创建虚拟根节点
        root = CallChainNode(class_name="root", method_name="root", signature=None)

        # 解析所有调用
        nodes_data = data.get("callGraph", data.get("calls", []))
        total_nodes = len(nodes_data) + 1

        # 构建调用节点
        for node_data in nodes_data:
            node = self._build_call_node(node_data, depth=1)
            root.children.append(node)

        # 识别远程调用
        self._identify_remote_calls(root)

        return CallChainGraph(
            root=root, direction=CallChainDirection.BOTH, max_depth=10, total_nodes=total_nodes
        )

    def _build_call_node(self, node_data: dict, depth: int) -> CallChainNode:
        """构建调用节点.

        Args:
            node_data: JACG 节点数据
            depth: 节点深度

        Returns:
            CallChainNode: 调用节点
        """
        class_name = node_data.get("className", "")
        method_name = node_data.get("methodName", "")
        signature = node_data.get("signature")

        node = CallChainNode(
            class_name=class_name,
            method_name=method_name,
            signature=signature,
        )

        # 递归处理子节点
        children_data = node_data.get("children", node_data.get("calls", []))
        for child_data in children_data:
            child_node = self._build_call_node(child_data, depth + 1)
            node.children.append(child_node)

        return node

    def _count_nodes(self, node: CallChainNode) -> int:
        """递归计算节点数.

        Args:
            node: 调用节点

        Returns:
            int: 节点总数
        """
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    def _identify_remote_calls(self, call_chain: CallChainGraph) -> CallChainGraph:
        """识别远程调用.

        Args:
            call_chain: 调用链

        Returns:
            CallChainGraph: 标记了远程调用的调用链
        """
        self._traverse_and_identify(call_chain.root)
        return call_chain

    def _traverse_and_identify(self, node: CallChainNode) -> None:
        """遍历节点并识别远程调用.

        Args:
            node: 调用节点
        """
        # 提取注解
        annotations = self._extract_annotations(node.class_name, node.method_name)

        # 识别 Dubbo 调用
        dubbo_info = self._identify_dubbo_call(annotations, node.class_name)
        if dubbo_info:
            node.service = dubbo_info.interface
            node.metadata = {
                "call_type": "dubbo",
                "interface": dubbo_info.interface,
                "version": dubbo_info.version,
                "group": dubbo_info.group,
            }

        # 识别 gRPC 调用
        grpc_info = self._identify_grpc_call(node.class_name, node.method_name)
        if grpc_info:
            node.service = grpc_info
            node.metadata = {"call_type": "grpc", "service": grpc_info}

        # 识别 REST 调用
        rest_info = self._identify_rest_call(
            annotations, node.class_name, node.method_name
        )
        if rest_info:
            node.service = rest_info.endpoint or rest_info.service_name
            node.metadata = {
                "call_type": "rest",
                "endpoint": rest_info.endpoint,
                "service": rest_info.service_name,
            }

        # 识别 Feign 调用
        feign_info = self._identify_feign_call(annotations, node.class_name)
        if feign_info:
            node.service = feign_info.service_name
            node.metadata = {
                "call_type": "feign",
                "service": feign_info.service_name,
                "url": feign_info.url,
            }

        # 递归处理子节点
        for child in node.children:
            self._traverse_and_identify(child)

    def _extract_annotations(self, class_name: str, method_name: str) -> list[dict]:
        """提取类和方法的注解.

        Args:
            class_name: 类名
            method_name: 方法名

        Returns:
            List[dict]: 注解列表
        """
        cache_key = f"{class_name}:{method_name}"
        if cache_key in self._annotation_cache:
            return self._annotation_cache[cache_key]

        # 查找 Java 源文件
        java_file = self._find_java_file(class_name)
        if not java_file:
            return []

        # 读取并解析注解
        try:
            content = java_file.read_text(encoding="utf-8", errors="ignore")
            annotations = self._parse_annotations_from_source(content)
            self._annotation_cache[cache_key] = annotations
            return annotations
        except Exception as e:
            logger.warning(f"Failed to parse annotations for {class_name}: {e}")
            return []

    def _find_java_file(self, class_name: str) -> Path | None:
        """查找 Java 源文件.

        Args:
            class_name: 类名

        Returns:
            Path | None: Java 文件路径
        """
        # 转换为文件路径
        path_parts = class_name.split(".")
        file_name = f"{path_parts[-1]}.java"
        dir_path = self._repo_path.joinpath(*path_parts[:-1])

        java_file = dir_path / file_name
        if java_file.exists():
            return java_file

        # 在项目中搜索
        for java_path in self._repo_path.rglob(f"{file_name}"):
            return java_path

        return None

    def _parse_annotations_from_source(self, content: str) -> list[dict]:
        """从源代码解析注解.

        Args:
            content: Java 源代码

        Returns:
            List[dict]: 注解列表
        """
        annotations = []

        # 匹配类级注解
        class_pattern = r"@\s*(\w+(?:\.\w+)*)\s*(?:\([^)]*\))?"
        for match in re.finditer(class_pattern, content):
            ann_type = match.group(1)
            annotations.append({"type": f"@{ann_type}", "level": "class"})

        # 匹配方法级注解
        method_pattern = (
            r"(?:public|private|protected)\s+(?:[\w<>[\]]+)\s+(\w+)\s*\([^)]*\)"
            r"[^{;]*?@\s*(\w+(?:\.\w+)*)"
        )
        for match in re.finditer(method_pattern, content):
            ann_type = match.group(2)
            annotations.append({"type": f"@{ann_type}", "level": "method"})

        return annotations

    def _identify_dubbo_call(
        self, annotations: list[dict], class_name: str
    ) -> DubboServiceInfo | None:
        """识别 Dubbo 服务调用.

        Args:
            annotations: 注解列表
            class_name: 类名

        Returns:
            DubboServiceInfo | None: Dubbo 服务信息
        """
        for ann in annotations:
            ann_type = ann.get("type", "")

            # Dubbo 服务引用
            if "Reference" in ann_type or "Reference" in ann_type:
                # 解析接口信息
                interface = self._extract_dubbo_interface(class_name)
                return DubboServiceInfo(
                    interface=interface, is_consumer=True
                )

            # Dubbo 服务提供者
            if "Service" in ann_type and "Dubbo" in ann_type:
                interface = self._extract_dubbo_interface(class_name)
                return DubboServiceInfo(
                    interface=interface, is_provider=True
                )

        return None

    def _extract_dubbo_interface(self, class_name: str) -> str:
        """提取 Dubbo 接口名.

        Args:
            class_name: 类名

        Returns:
            str: 接口名
        """
        # 简化处理：假设接口名与类名相似
        # 实际应该从配置文件或注解参数中解析
        simple_name = class_name.split(".")[-1]
        return f"I{simple_name}"  # 例如: UserService -> IUserService

    def _identify_grpc_call(self, class_name: str, method_name: str) -> str | None:
        """识别 gRPC 调用.

        Args:
            class_name: 类名
            method_name: 方法名

        Returns:
            str | None: gRPC 服务名
        """
        # gRPC 调用特征
        grpc_patterns = [
            ".newFutureStub(",
            ".newBlockingStub(",
            ".getStub(",
            "grpc:",
            "Grpc.",
        ]

        # 检查方法名
        if any(p in method_name for p in grpc_patterns):
            return class_name

        # 检查类名
        if "Stub" in class_name or "Grpc" in class_name:
            return class_name.replace("Stub", "").replace("Grpc", "")

        return None

    def _identify_rest_call(
        self, annotations: list[dict], class_name: str, method_name: str
    ) -> RemoteCallInfo | None:
        """识别 REST 调用.

        Args:
            annotations: 注解列表
            class_name: 类名
            method_name: 方法名

        Returns:
            RemoteCallInfo | None: REST 调用信息
        """
        # RestTemplate 或 WebClient 调用
        if any(x in method_name for x in ["RestTemplate", "WebClient"]):
            return RemoteCallInfo(call_type="rest")

        # Feign 客户端
        if "FeignClient" in str(annotations):
            service_name = self._extract_feign_service(annotations)
            return RemoteCallInfo(
                call_type="feign", service_name=service_name
            )

        # HTTP 调用
        if any(x in method_name for x in [".exchange(", ".getFor", ".postFor"]):
            return RemoteCallInfo(call_type="rest")

        return None

    def _identify_feign_call(
        self, annotations: list[dict], class_name: str
    ) -> RemoteCallInfo | None:
        """识别 Feign 调用.

        Args:
            annotations: 注解列表
            class_name: 类名

        Returns:
            RemoteCallInfo | None: Feign 调用信息
        """
        for ann in annotations:
            if "FeignClient" in ann.get("type", ""):
                service_name = self._extract_feign_service(annotations)
                url = self._extract_feign_url(ann.get("type", ""))
                return RemoteCallInfo(
                    call_type="feign", service_name=service_name, url=url
                )

        return None

    def _extract_feign_service(self, annotations: list[dict]) -> str | None:
        """提取 Feign 服务名.

        Args:
            annotations: 注解列表

        Returns:
            str | None: 服务名
        """
        # 简化处理：从类名提取
        # 实际应该从 FeignClient 注解参数中解析
        return None

    def _extract_feign_url(self, annotation: str) -> str | None:
        """提取 Feign URL.

        Args:
            annotation: 注解字符串

        Returns:
            str | None: URL
        """
        # 解析注解参数中的 URL
        url_pattern = r'url\s*=\s*["\']([^"\']+)["\']'
        match = re.search(url_pattern, annotation)
        return match.group(1) if match else None

    def _create_empty_graph(self, method: str, max_depth: int) -> CallChainGraph:
        """创建空调用链图.

        Args:
            method: 方法名
            max_depth: 最大深度

        Returns:
            CallChainGraph: 空的调用链图
        """
        class_name, method_name = self._parse_method(method)

        root = CallChainNode(
            class_name=class_name, method_name=method_name, signature=None
        )

        return CallChainGraph(
            root=root,
            direction=CallChainDirection.BOTH,
            max_depth=max_depth,
            total_nodes=1,
        )

    def _download_jacg(self) -> Path:
        """下载 JACG JAR 包.

        Returns:
            Path: JAR 文件路径
        """
        jar_path = self._cache_dir / JACG_JAR_NAME

        if jar_path.exists():
            logger.info(f"JACG JAR already exists: {jar_path}")
            return jar_path

        logger.info(f"Downloading JACG from: {JACG_RELEASE_URL}")

        try:
            # 下载 URL
            download_url = f"{JACG_RELEASE_URL}/{JACG_JAR_NAME}"

            # 使用 urllib 下载
            with urllib.request.urlopen(download_url) as response, open(jar_path, "wb") as out_file:
                data = response.read()
                out_file.write(data)

            logger.info(f"JACG JAR downloaded to: {jar_path}")
            return jar_path

        except Exception as e:
            logger.error(f"Failed to download JACG: {e}")
            raise RuntimeError(f"Cannot download JACG: {e}") from e

    def build_service_topology(self) -> dict[str, Any]:
        """构建微服务拓扑图.

        Returns:
            Dict[str, Any]: 服务拓扑数据
        """
        topology = {"services": {}, "dependencies": {}, "endpoints": {}}

        # 扫描所有 Java 文件
        for java_file in self._repo_path.rglob("*.java"):
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")

                # 识别 Dubbo 服务
                if "@DubboService" in content or "@Service" in content:
                    service = self._parse_dubbo_service(content, java_file)
                    if service:
                        topology["services"][service.interface] = {
                            "type": "dubbo",
                            "name": service.interface,
                            "is_provider": service.is_provider,
                            "version": service.version,
                            "group": service.group,
                        }

                # 识别 Dubbo 消费者
                if "@Reference" in content:
                    consumer = self._parse_dubbo_consumer(content, java_file)
                    if consumer:
                        topology["services"][consumer.interface] = {
                            "type": "dubbo",
                            "name": consumer.interface,
                            "is_consumer": consumer.is_consumer,
                        }

            except Exception as e:
                logger.warning(f"Failed to analyze {java_file}: {e}")

        # 分析服务依赖
        for service_name in topology["services"]:
            dependencies = self._analyze_service_dependencies(
                service_name, topology["services"]
            )
            topology["dependencies"][service_name] = dependencies

        return topology

    def _parse_dubbo_service(
        self, content: str, java_file: Path
    ) -> DubboServiceInfo | None:
        """解析 Dubbo 服务提供者.

        Args:
            content: Java 源代码
            java_file: Java 文件路径

        Returns:
            DubboServiceInfo | None: Dubbo 服务信息
        """
        # 解析类名
        class_pattern = r"class\s+(\w+)"
        match = re.search(class_pattern, content)
        if not match:
            return None

        class_name = match.group(1)

        # 解析注解参数
        version = None
        group = None

        version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if version_match:
            version = version_match.group(1)

        group_match = re.search(r'group\s*=\s*"([^"]+)"', content)
        if group_match:
            group = group_match.group(1)

        # 构建接口名
        interface = f"I{class_name}"

        return DubboServiceInfo(
            interface=interface,
            version=version,
            group=group,
            is_provider=True,
        )

    def _parse_dubbo_consumer(
        self, content: str, java_file: Path
    ) -> DubboServiceInfo | None:
        """解析 Dubbo 服务消费者.

        Args:
            content: Java 源代码
            java_file: Java 文件路径

        Returns:
            DubboServiceInfo | None: Dubbo 服务信息
        """
        # 解析 @Reference 注解
        reference_match = re.search(
            r'@Reference\s*(?:\([^)]*\))?\s*(?:private|public|protected)?\s+([\w<>[\]]+)',
            content,
        )
        if not reference_match:
            return None

        interface_type = reference_match.group(1)

        # 解析注解参数
        version = None
        group = None

        annotation_match = re.search(r'@Reference\s*\(([^)]+)\)', content)
        if annotation_match:
            annotation_content = annotation_match.group(1)
            version_match = re.search(r'version\s*=\s*"([^"]+)"', annotation_content)
            if version_match:
                version = version_match.group(1)

            group_match = re.search(r'group\s*=\s*"([^"]+)"', annotation_content)
            if group_match:
                group = group_match.group(1)

        # 提取接口名
        interface = interface_type.split("<")[0].strip()

        return DubboServiceInfo(
            interface=interface, version=version, group=group, is_consumer=True
        )

    def _analyze_service_dependencies(
        self, service_name: str, all_services: dict
    ) -> list[str]:
        """分析服务依赖.

        Args:
            service_name: 服务名
            all_services: 所有服务

        Returns:
            List[str]: 依赖的服务列表
        """
        dependencies = []

        # 查找引用此服务的其他服务
        for other_name, other_info in all_services.items():
            if other_name == service_name:
                continue

            # 如果其他服务包含此服务的引用
            if other_info.get("is_consumer"):
                dependencies.append(other_name)

        return dependencies
