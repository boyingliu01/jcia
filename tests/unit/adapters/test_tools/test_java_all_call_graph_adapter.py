"""Java All Call Graph 适配器单元测试."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from jcia.adapters.tools.java_all_call_graph_adapter import (
    DubboServiceInfo,
    JavaAllCallGraphAdapter,
    RemoteCallInfo,
)
from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create temporary project directory structure."""
    # Create source directory structure
    src_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Create a simple Java file
    java_file = src_dir / "Service.java"
    java_file.write_text("""
package com.example;

public class Service {
    public void method1() {
        helper.method();
    }

    public void method2() {
        helper.anotherMethod();
    }
}
""")

    return tmp_path


class TestJavaAllCallGraphAdapter:
    """JavaAllCallGraphAdapter 测试类."""

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    @patch("jcia.adapters.tools.java_all_call_graph_adapter.Path.exists")
    def test_init_downloads_jacg_if_not_exists(
        self, mock_exists, mock_run, tmp_path: Path
    ) -> None:
        """测试初始化时下载 JACG 如果不存在."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create a fake JAR file in cache to avoid download
        fake_jar = cache_dir / "java-all-call-graph-0.9.0-jar-with-dependencies.jar"
        fake_jar.touch()

        mock_exists.return_value = True

        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            cache_dir=cache_dir,
        )

        assert adapter._cache_dir == cache_dir
        assert adapter._max_depth == 10

    def test_init_with_custom_jar(self, tmp_path: Path) -> None:
        """测试使用自定义 JAR 路径初始化."""
        custom_jar = tmp_path / "custom.jar"
        custom_jar.touch()

        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(custom_jar),
        )

        assert adapter._jacg_jar == custom_jar

    def test_init_resolves_repo_path(self, tmp_path: Path) -> None:
        """测试初始化解析仓库路径."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path / "repo"),
            jacg_jar=tmp_path / "test.jar",
        )

        assert adapter._repo_path.is_absolute()

    def test_analyzer_type_returns_static(self, tmp_path: Path) -> None:
        """测试分析器类型返回 STATIC."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        assert adapter.analyzer_type == AnalyzerType.STATIC

    def test_supports_cross_service_returns_false(self, tmp_path: Path) -> None:
        """测试跨服务支持返回 False."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        assert adapter.supports_cross_service is False

    def test_parse_method_valid(self, tmp_path: Path) -> None:
        """测试解析有效方法名."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        class_name, method_name = adapter._parse_method("com.example.Service.method1")

        assert class_name == "com.example.Service"
        assert method_name == "method1"

    def test_parse_method_invalid(self, tmp_path: Path) -> None:
        """测试解析无效方法名."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        class_name, method_name = adapter._parse_method("method1")

        assert class_name == "method1"
        assert method_name == "method1"

    def test_create_empty_graph(self, tmp_path: Path) -> None:
        """测试创建空调用链图."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        graph = adapter._create_empty_graph("com.example.Service.method1", 5)

        assert isinstance(graph, CallChainGraph)
        assert graph.root.class_name == "com.example.Service"
        assert graph.root.method_name == "method1"
        assert graph.max_depth == 5
        assert graph.total_nodes == 1

    def test_find_java_file_existing(self, tmp_path: Path) -> None:
        """测试查找存在的 Java 文件."""
        src_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
        src_dir.mkdir(parents=True, exist_ok=True)
        java_file = src_dir / "Service.java"
        java_file.write_text("public class Service {}")

        adapter = JavaAllCallGraphAdapter(
            repo_path=tmp_path,
            jacg_jar=tmp_path / "test.jar",
        )

        result = adapter._find_java_file("com.example.Service")

        assert result is not None
        assert result.name == "Service.java"

    def test_find_java_file_not_found(self, tmp_path: Path) -> None:
        """测试查找不存在的 Java 文件."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=tmp_path,
            jacg_jar=tmp_path / "test.jar",
        )

        result = adapter._find_java_file("com.example.NonExistent")

        assert result is None

    def test_parse_annotations_from_source(self, tmp_path: Path) -> None:
        """测试从源代码解析注解."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        content = """
@Deprecated
@Service
public class Service {
    @Override
    public void method1() {}
}
"""
        annotations = adapter._parse_annotations_from_source(content)

        assert len(annotations) > 0
        assert any("@Deprecated" in ann["type"] for ann in annotations)
        assert any("@Service" in ann["type"] for ann in annotations)

    def test_identify_dubbo_call_with_reference(self, tmp_path: Path) -> None:
        """测试识别 Dubbo 调用（@Reference）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        annotations = [{"type": "@Reference", "level": "field"}]

        result = adapter._identify_dubbo_call(annotations, "com.example.Consumer")

        assert result is not None
        assert result.interface == "IConsumer"
        assert result.is_consumer is True

    def test_identify_dubbo_call_with_service(self, tmp_path: Path) -> None:
        """测试识别 Dubbo 调用（@DubboService）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        annotations = [{"type": "@DubboService", "level": "class"}]

        result = adapter._identify_dubbo_call(annotations, "com.example.Provider")

        assert result is not None
        assert result.is_provider is True

    def test_identify_dubbo_call_none(self, tmp_path: Path) -> None:
        """测试不识别非 Dubbo 调用."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        annotations = [{"type": "@Component", "level": "class"}]

        result = adapter._identify_dubbo_call(annotations, "com.example.Service")

        assert result is None

    def test_identify_grpc_call_with_stub(self, tmp_path: Path) -> None:
        """测试识别 gRPC 调用（Stub）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        result = adapter._identify_grpc_call("com.example.ServiceStub", "newFutureStub")

        assert result is not None
        assert "Service" in result

    def test_identify_grpc_call_none(self, tmp_path: Path) -> None:
        """测试不识别非 gRPC 调用."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        result = adapter._identify_grpc_call("com.example.Service", "regularMethod")

        assert result is None

    def test_identify_rest_call_with_rest_template(self, tmp_path: Path) -> None:
        """测试识别 REST 调用（RestTemplate）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        # RestTemplate is checked with exact match
        result = adapter._identify_rest_call(
            [], "com.example.Client", "RestTemplateExchange"
        )

        assert result is not None
        assert result.call_type == "rest"

    def test_identify_rest_call_with_web_client(self, tmp_path: Path) -> None:
        """测试识别 REST 调用（WebClient）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        # WebClient is also checked
        result = adapter._identify_rest_call(
            [], "com.example.Client", "WebClientCall"
        )

        assert result is not None
        assert result.call_type == "rest"

    def test_identify_rest_call_with_exchange(self, tmp_path: Path) -> None:
        """测试识别 REST 调用（.exchange）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        # .exchange( is checked as part of method name
        result = adapter._identify_rest_call(
            [], "com.example.Client", ".exchange(some, args)"
        )

        assert result is not None
        assert result.call_type == "rest"

    def test_identify_rest_call_none(self, tmp_path: Path) -> None:
        """测试不识别非 REST 调用."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        result = adapter._identify_rest_call([], "com.example.Client", "regularMethod")

        assert result is None

    def test_extract_feign_url(self, tmp_path: Path) -> None:
        """测试提取 Feign URL."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        annotation = '@FeignClient(url="http://example.com/api")'
        result = adapter._extract_feign_url(annotation)

        assert result == "http://example.com/api"

    def test_extract_feign_url_none(self, tmp_path: Path) -> None:
        """测试提取 Feign URL（无 URL）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        annotation = "@FeignClient"
        result = adapter._extract_feign_url(annotation)

        assert result is None

    def test_build_call_node(self, tmp_path: Path) -> None:
        """测试构建调用节点."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        node_data = {
            "className": "com.example.Service",
            "methodName": "method1",
            "signature": "()V",
            "children": [
                {
                    "className": "com.example.Helper",
                    "methodName": "helperMethod",
                    "signature": "()V",
                    "children": [],
                }
            ],
        }

        node = adapter._build_call_node(node_data, depth=1)

        assert node.class_name == "com.example.Service"
        assert node.method_name == "method1"
        assert node.signature == "()V"
        assert len(node.children) == 1
        assert node.children[0].class_name == "com.example.Helper"

    def test_count_nodes(self, tmp_path: Path) -> None:
        """测试计算节点数."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        root = CallChainNode(
            class_name="Service",
            method_name="root",
            signature=None,
        )
        child1 = CallChainNode(
            class_name="Helper",
            method_name="method1",
            signature=None,
        )
        child2 = CallChainNode(
            class_name="Helper",
            method_name="method2",
            signature=None,
        )
        root.children.extend([child1, child2])

        count = adapter._count_nodes(root)

        assert count == 3

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    def test_build_full_graph_success(self, mock_run, tmp_path: Path) -> None:
        """测试构建完整调用图（成功）。"""
        # Mock successful subprocess
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Create output file
        output_dir = tmp_path / ".jcia" / "jacg"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "full_call_graph.json"
        output_file.write_text('{"callGraph": []}')

        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        graph = adapter.build_full_graph()

        assert isinstance(graph, CallChainGraph)
        assert graph.root.class_name == "root"

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    def test_build_full_graph_failure(self, mock_run, tmp_path: Path) -> None:
        """测试构建完整调用图（失败）。"""
        # Mock failed subprocess
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error occurred"
        mock_run.return_value = mock_result

        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        graph = adapter.build_full_graph()

        assert isinstance(graph, CallChainGraph)
        assert graph.root.class_name == "root"

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    @patch("jcia.adapters.tools.java_all_call_graph_adapter.Path.exists")
    def test_analyze_upstream_cached(
        self, mock_exists, mock_run, tmp_path: Path
    ) -> None:
        """测试分析上游（使用缓存）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        # Set up cache
        cached_graph = CallChainGraph(
            root=CallChainNode(
                class_name="Service",
                method_name="method1",
                signature=None,
            ),
            direction=CallChainDirection.UPSTREAM,
            max_depth=5,
            total_nodes=1,
        )
        adapter._call_cache["upstream:Service.method1:5"] = cached_graph

        result = adapter.analyze_upstream("Service.method1", 5)

        assert result == cached_graph
        # subprocess.run should not be called due to cache
        mock_run.assert_not_called()

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    @patch("jcia.adapters.tools.java_all_call_graph_adapter.Path.exists")
    def test_analyze_downstream(
        self, mock_exists, mock_run, tmp_path: Path
    ) -> None:
        """测试分析下游."""
        # Mock subprocess
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Mock file exists
        mock_exists.return_value = True

        # Create output file
        output_dir = tmp_path / ".jcia" / "jacg"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "downstream_hash.json"
        output_file.write_text('{"callGraph": []}')

        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        result = adapter.analyze_downstream("Service.method1", 5)

        assert isinstance(result, CallChainGraph)

    def test_analyze_both_directions(self, tmp_path: Path) -> None:
        """测试同时分析上下游."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=tmp_path / "test.jar",
        )

        # Mock analyze methods
        upstream_graph = CallChainGraph(
            root=CallChainNode(class_name="A", method_name="m", signature=None),
            direction=CallChainDirection.UPSTREAM,
            max_depth=5,
            total_nodes=1,
        )
        downstream_graph = CallChainGraph(
            root=CallChainNode(class_name="B", method_name="m", signature=None),
            direction=CallChainDirection.DOWNSTREAM,
            max_depth=5,
            total_nodes=1,
        )

        adapter.analyze_upstream = Mock(return_value=upstream_graph)  # type: ignore[method-assign]
        adapter.analyze_downstream = Mock(return_value=downstream_graph)  # type: ignore[method-assign]

        upstream, downstream = adapter.analyze_both_directions("Service.method1", 5)

        assert upstream == upstream_graph
        assert downstream == downstream_graph
        adapter.analyze_upstream.assert_called_once_with("Service.method1", 5)
        adapter.analyze_downstream.assert_called_once_with("Service.method1", 5)


class TestDubboServiceInfo:
    """DubboServiceInfo 测试类."""

    def test_dubbo_service_info_init(self) -> None:
        """测试 DubboServiceInfo 初始化."""
        info = DubboServiceInfo(
            interface="com.example.IUserService",
            version="1.0.0",
            group="default",
            is_consumer=True,
            is_provider=False,
        )

        assert info.interface == "com.example.IUserService"
        assert info.version == "1.0.0"
        assert info.group == "default"
        assert info.is_consumer is True
        assert info.is_provider is False

    def test_dubbo_service_info_defaults(self) -> None:
        """测试 DubboServiceInfo 默认值."""
        info = DubboServiceInfo(interface="com.example.IUserService")

        assert info.version is None
        assert info.group is None
        assert info.is_consumer is False
        assert info.is_provider is False


class TestRemoteCallInfo:
    """RemoteCallInfo 测试类."""

    def test_remote_call_info_init(self) -> None:
        """测试 RemoteCallInfo 初始化."""
        info = RemoteCallInfo(
            call_type="dubbo",
            service_name="userService",
            interface="com.example.IUserService",
            endpoint="/api/user",
            method="getUser",
            url="http://localhost:8080",
        )

        assert info.call_type == "dubbo"
        assert info.service_name == "userService"
        assert info.interface == "com.example.IUserService"
        assert info.endpoint == "/api/user"
        assert info.method == "getUser"
        assert info.url == "http://localhost:8080"

    def test_remote_call_info_defaults(self) -> None:
        """测试 RemoteCallInfo 默认值."""
        info = RemoteCallInfo(call_type="rest")

        assert info.service_name is None
        assert info.interface is None
        assert info.endpoint is None
        assert info.method is None
        assert info.url is None
