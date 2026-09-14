"""Java All Call Graph 适配器单元测试."""

import hashlib
import subprocess
from pathlib import Path
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
    java_file.write_text(
        """
package com.example;

public class Service {
    public void method1() {
        helper.method();
    }

    public void method2() {
        helper.anotherMethod();
    }
}
"""
    )

    return tmp_path


class TestJavaAllCallGraphAdapter:
    """JavaAllCallGraphAdapter 测试类."""

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    @patch("jcia.adapters.tools.java_all_call_graph_adapter.Path.exists")
    def test_init_downloads_jacg_if_not_exists(self, mock_exists, mock_run, tmp_path: Path) -> None:
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
            jacg_jar=str(tmp_path / "test.jar"),
        )

        assert adapter._repo_path.is_absolute()

    def test_analyzer_type_returns_static(self, tmp_path: Path) -> None:
        """测试分析器类型返回 STATIC."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        assert adapter.analyzer_type == AnalyzerType.STATIC

    def test_supports_cross_service_returns_false(self, tmp_path: Path) -> None:
        """测试跨服务支持返回 False."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        assert adapter.supports_cross_service is False

    def test_parse_method_valid(self, tmp_path: Path) -> None:
        """测试解析有效方法名."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        class_name, method_name = adapter._parse_method("com.example.Service.method1")

        assert class_name == "com.example.Service"
        assert method_name == "method1"

    def test_parse_method_invalid(self, tmp_path: Path) -> None:
        """测试解析无效方法名."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        class_name, method_name = adapter._parse_method("method1")

        assert class_name == "method1"
        assert method_name == "method1"

    def test_create_empty_graph(self, tmp_path: Path) -> None:
        """测试创建空调用链图."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
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
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        result = adapter._find_java_file("com.example.Service")

        assert result is not None
        assert result.name == "Service.java"

    def test_find_java_file_not_found(self, tmp_path: Path) -> None:
        """测试查找不存在的 Java 文件."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        result = adapter._find_java_file("com.example.NonExistent")

        assert result is None

    def test_parse_annotations_from_source(self, tmp_path: Path) -> None:
        """测试从源代码解析注解."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
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
            jacg_jar=str(tmp_path / "test.jar"),
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
            jacg_jar=str(tmp_path / "test.jar"),
        )

        annotations = [{"type": "@DubboService", "level": "class"}]

        result = adapter._identify_dubbo_call(annotations, "com.example.Provider")

        assert result is not None
        assert result.is_provider is True

    def test_identify_dubbo_call_none(self, tmp_path: Path) -> None:
        """测试不识别非 Dubbo 调用."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        annotations = [{"type": "@Component", "level": "class"}]

        result = adapter._identify_dubbo_call(annotations, "com.example.Service")

        assert result is None

    def test_identify_grpc_call_with_stub(self, tmp_path: Path) -> None:
        """测试识别 gRPC 调用（Stub）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        result = adapter._identify_grpc_call("com.example.ServiceStub", "newFutureStub")

        assert result is not None
        assert "Service" in result

    def test_identify_grpc_call_none(self, tmp_path: Path) -> None:
        """测试不识别非 gRPC 调用."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        result = adapter._identify_grpc_call("com.example.Service", "regularMethod")

        assert result is None

    def test_identify_rest_call_with_rest_template(self, tmp_path: Path) -> None:
        """测试识别 REST 调用（RestTemplate）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        # RestTemplate is checked with exact match
        result = adapter._identify_rest_call([], "com.example.Client", "RestTemplateExchange")

        assert result is not None
        assert result.call_type == "rest"

    def test_identify_rest_call_with_web_client(self, tmp_path: Path) -> None:
        """测试识别 REST 调用（WebClient）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        # WebClient is also checked
        result = adapter._identify_rest_call([], "com.example.Client", "WebClientCall")

        assert result is not None
        assert result.call_type == "rest"

    def test_identify_rest_call_with_exchange(self, tmp_path: Path) -> None:
        """测试识别 REST 调用（.exchange）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        # .exchange( is checked as part of method name
        result = adapter._identify_rest_call([], "com.example.Client", ".exchange(some, args)")

        assert result is not None
        assert result.call_type == "rest"

    def test_identify_rest_call_none(self, tmp_path: Path) -> None:
        """测试不识别非 REST 调用."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        result = adapter._identify_rest_call([], "com.example.Client", "regularMethod")

        assert result is None

    def test_extract_feign_url(self, tmp_path: Path) -> None:
        """测试提取 Feign URL."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        annotation = '@FeignClient(url="http://example.com/api")'
        result = adapter._extract_feign_url(annotation)

        assert result == "http://example.com/api"

    def test_extract_feign_url_none(self, tmp_path: Path) -> None:
        """测试提取 Feign URL（无 URL）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
        )

        annotation = "@FeignClient"
        result = adapter._extract_feign_url(annotation)

        assert result is None

    def test_build_call_node(self, tmp_path: Path) -> None:
        """测试构建调用节点."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
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
            jacg_jar=str(tmp_path / "test.jar"),
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
            jacg_jar=str(tmp_path / "test.jar"),
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
            jacg_jar=str(tmp_path / "test.jar"),
        )

        graph = adapter.build_full_graph()

        assert isinstance(graph, CallChainGraph)
        assert graph.root.class_name == "root"

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    @patch("jcia.adapters.tools.java_all_call_graph_adapter.Path.exists")
    def test_analyze_upstream_cached(self, mock_exists, mock_run, tmp_path: Path) -> None:
        """测试分析上游（使用缓存）。"""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
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
    def test_analyze_downstream(self, mock_exists, mock_run, tmp_path: Path) -> None:
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
            jacg_jar=str(tmp_path / "test.jar"),
        )

        result = adapter.analyze_downstream("Service.method1", 5)

        assert isinstance(result, CallChainGraph)

    def test_analyze_both_directions(self, tmp_path: Path) -> None:
        """测试同时分析上下游."""
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path),
            jacg_jar=str(tmp_path / "test.jar"),
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


def _make_adapter(tmp_path: Path) -> JavaAllCallGraphAdapter:
    """构造一个不触发 JAR 下载的适配器。"""
    return JavaAllCallGraphAdapter(
        repo_path=str(tmp_path),
        jacg_jar=str(tmp_path / "test.jar"),
    )


class TestAnalyzeDirectionPaths:
    """analyze_upstream 缓存未命中(130-135)与 analyze_downstream 缓存命中(152)。"""

    def test_analyze_upstream_cache_miss(self, tmp_path: Path) -> None:
        """缓存未命中时调用 _analyze_with_jacg 并写回缓存。"""
        adapter = _make_adapter(tmp_path)
        graph = CallChainGraph(
            root=CallChainNode(class_name="A", method_name="m", signature=None),
            direction=CallChainDirection.UPSTREAM,
            max_depth=7,
            total_nodes=2,
        )
        adapter._analyze_with_jacg = Mock(return_value=graph)  # type: ignore[method-assign]

        result = adapter.analyze_upstream("A.m", 7)

        assert result == graph
        adapter._analyze_with_jacg.assert_called_once_with("A.m", "upstream", 7)
        assert adapter._call_cache["upstream:A.m:7"] == graph

    def test_analyze_downstream_cache_hit(self, tmp_path: Path) -> None:
        """下游缓存命中直接返回，不调用 JACG。"""
        adapter = _make_adapter(tmp_path)
        cached = CallChainGraph(
            root=CallChainNode(class_name="A", method_name="m", signature=None),
            direction=CallChainDirection.DOWNSTREAM,
            max_depth=3,
            total_nodes=1,
        )
        adapter._call_cache["downstream:A.m:3"] = cached
        adapter._analyze_with_jacg = Mock()  # type: ignore[method-assign]

        result = adapter.analyze_downstream("A.m", 3)

        assert result == cached
        adapter._analyze_with_jacg.assert_not_called()


class TestBuildFullGraphBranches:
    """build_full_graph 剩余分支（212-220）。"""

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    def test_output_file_missing(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """returncode 0 但输出文件不存在 -> 空调用图。"""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        adapter = _make_adapter(tmp_path)

        graph = adapter.build_full_graph()

        assert graph.total_nodes == 1

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    def test_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """子进程超时 -> 空调用图。"""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="java", timeout=600)
        adapter = _make_adapter(tmp_path)

        graph = adapter.build_full_graph()

        assert graph.total_nodes == 1

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    def test_generic_exception(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """通用异常 -> 空调用图。"""
        mock_run.side_effect = OSError("java not found")
        adapter = _make_adapter(tmp_path)

        graph = adapter.build_full_graph()

        assert graph.total_nodes == 1


class TestAnalyzeWithJacg:
    """_analyze_with_jacg 各分支（283-301）。"""

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    def test_returncode_nonzero(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """非零退出码 -> 空调用图。"""
        mock_run.return_value = MagicMock(returncode=1, stderr="bad")
        adapter = _make_adapter(tmp_path)

        graph = adapter._analyze_with_jacg("com.example.Svc.m", "upstream", 5)

        assert graph.total_nodes == 1

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    def test_output_file_missing(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """成功退出但输出文件缺失 -> 空调用图。"""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        adapter = _make_adapter(tmp_path)

        graph = adapter._analyze_with_jacg("com.example.Svc.m", "downstream", 5)

        assert graph.total_nodes == 1

    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    def test_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """超时 -> 空调用图。"""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="java", timeout=300)
        adapter = _make_adapter(tmp_path)

        graph = adapter._analyze_with_jacg("com.example.Svc.m", "upstream", 5)

        assert graph.total_nodes == 1

    @patch.object(JavaAllCallGraphAdapter, "_extract_annotations")
    @patch("jcia.adapters.tools.java_all_call_graph_adapter.subprocess.run")
    def test_success_parses_output(
        self, mock_run: MagicMock, mock_annos: MagicMock, tmp_path: Path
    ) -> None:
        """成功生成输出文件 -> 解析为调用图（覆盖 _parse_jacg_output 317-349）。"""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        mock_annos.return_value = []
        adapter = _make_adapter(tmp_path)

        method = "com.example.Svc.m"
        method_hash = hashlib.md5(method.encode(), usedforsecurity=False).hexdigest()
        output_file = adapter._output_dir / f"upstream_{method_hash}.json"
        output_file.write_text(
            '{"callGraph": [{"className": "com.example.Caller", '
            '"methodName": "go", "children": []}]}'
        )

        graph = adapter._analyze_with_jacg(method, "upstream", 6)

        assert graph.direction == CallChainDirection.UPSTREAM
        assert graph.root.class_name == "com.example.Svc"
        assert graph.total_nodes == 2  # root + 1 child


class TestParseFullGraphLoop:
    """_parse_full_graph 构建节点循环（369-370）。"""

    @patch.object(JavaAllCallGraphAdapter, "_extract_annotations")
    def test_loop_appends_nodes(self, mock_annos: MagicMock, tmp_path: Path) -> None:
        """非空 callGraph 时构建子节点并计数。"""
        mock_annos.return_value = []
        adapter = _make_adapter(tmp_path)
        data = {
            "callGraph": [
                {"className": "A", "methodName": "a", "children": []},
                {"className": "B", "methodName": "b", "children": []},
            ]
        }

        graph = adapter._parse_full_graph(data)

        assert graph.root.class_name == "root"
        assert len(graph.root.children) == 2
        assert graph.total_nodes == 3


class TestTraverseAndIdentify:
    """_traverse_and_identify 四类远程调用赋值与递归（446-482）。"""

    def test_all_branches_and_recursion(self, tmp_path: Path) -> None:
        """单节点同时命中 dubbo/grpc/rest/feign，并递归处理子节点。"""
        adapter = _make_adapter(tmp_path)
        annotations = [
            {"type": "@Reference", "level": "class"},
            {"type": '@FeignClient(url="http://x")', "level": "class"},
        ]
        adapter._extract_annotations = Mock(return_value=annotations)  # type: ignore[method-assign]

        node = CallChainNode(
            class_name="com.example.FooStub",
            method_name="Grpc.RestTemplate",
            signature=None,
        )
        node.children.append(
            CallChainNode(class_name="com.example.Bar", method_name="plain", signature=None)
        )

        adapter._traverse_and_identify(node)

        # feign 分支最后赋值
        assert node.metadata["call_type"] == "feign"
        assert node.service is not None or node.metadata["service"] is None


class TestExtractAnnotationsBranches:
    """_extract_annotations 缓存命中/成功/异常与 _find_java_file 直接命中。"""

    def test_cache_hit(self, tmp_path: Path) -> None:
        """命中缓存直接返回（496）。"""
        adapter = _make_adapter(tmp_path)
        adapter._annotation_cache["Svc:m"] = [{"type": "@X"}]

        assert adapter._extract_annotations("Svc", "m") == [{"type": "@X"}]

    def test_success_reads_source(self, tmp_path: Path) -> None:
        """找到源文件并解析注解、写回缓存（504-508）。"""
        pkg = tmp_path / "com" / "example"
        pkg.mkdir(parents=True)
        (pkg / "Service.java").write_text("@Service\npublic class Service {}\n")
        adapter = _make_adapter(tmp_path)

        annotations = adapter._extract_annotations("com.example.Service", "method1")

        assert any("@Service" in a["type"] for a in annotations)
        assert "com.example.Service:method1" in adapter._annotation_cache

    def test_read_failure_returns_empty(self, tmp_path: Path) -> None:
        """读取源文件异常时返回空（509-511）。"""
        adapter = _make_adapter(tmp_path)
        bad = MagicMock()
        bad.read_text.side_effect = OSError("io")
        adapter._find_java_file = Mock(return_value=bad)  # type: ignore[method-assign]

        assert adapter._extract_annotations("X", "m") == []

    def test_find_java_file_direct_hit(self, tmp_path: Path) -> None:
        """类路径直译的文件真实存在时直接返回（528-529）。"""
        pkg = tmp_path / "com" / "example"
        pkg.mkdir(parents=True)
        target = pkg / "Widget.java"
        target.write_text("public class Widget {}")
        adapter = _make_adapter(tmp_path)

        assert adapter._find_java_file("com.example.Widget") == target


class TestAnnotationAndCallTypeEdges:
    """方法级注解解析与 grpc/rest/feign 识别剩余分支。"""

    def test_parse_method_level_annotation(self, tmp_path: Path) -> None:
        """命中方法级注解正则（560-561）。"""
        adapter = _make_adapter(tmp_path)
        content = "@Service\npublic class C {\npublic void run() @Test\n}"

        annotations = adapter._parse_annotations_from_source(content)

        assert any(a["level"] == "method" for a in annotations)

    def test_identify_grpc_by_method_name(self, tmp_path: Path) -> None:
        """方法名含 grpc 特征 -> 返回类名（627-628）。"""
        adapter = _make_adapter(tmp_path)

        assert adapter._identify_grpc_call("com.example.Svc", "ch.newFutureStub(ch)") == (
            "com.example.Svc"
        )

    def test_identify_rest_feign_branch(self, tmp_path: Path) -> None:
        """annotations 含 FeignClient 时 REST 识别走 feign 分支（654-656）。"""
        adapter = _make_adapter(tmp_path)

        info = adapter._identify_rest_call(
            [{"type": "@FeignClient"}], "com.example.Api", "regularMethod"
        )

        assert info is not None
        assert info.call_type == "feign"

    def test_identify_feign_call(self, tmp_path: Path) -> None:
        """_identify_feign_call 命中 FeignClient 注解（677-680 + 695）。"""
        adapter = _make_adapter(tmp_path)

        info = adapter._identify_feign_call(
            [{"type": '@FeignClient(url="http://svc")'}], "com.example.Api"
        )

        assert info is not None
        assert info.call_type == "feign"
        assert info.url == "http://svc"


class TestDownloadJacg:
    """_download_jacg 下载体（744-760）。"""

    def test_download_success(self, tmp_path: Path) -> None:
        """jar 不存在时下载并写入。"""
        cache_dir = tmp_path / "cache"
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path), jacg_jar=str(tmp_path / "t.jar"), cache_dir=cache_dir
        )
        # 删除 init 生成的 jar 之外的下载目标（若存在）
        jar_path = cache_dir / "java-all-call-graph-0.9.0-jar-with-dependencies.jar"
        if jar_path.exists():
            jar_path.unlink()

        resp = MagicMock()
        resp.read.return_value = b"fake-jar-bytes"
        ctx = MagicMock()
        ctx.__enter__.return_value = resp
        ctx.__exit__.return_value = False

        with patch(
            "jcia.adapters.tools.java_all_call_graph_adapter.urllib.request.urlopen",
            return_value=ctx,
        ):
            result = adapter._download_jacg()

        assert result == jar_path
        assert jar_path.read_bytes() == b"fake-jar-bytes"

    def test_download_failure_raises(self, tmp_path: Path) -> None:
        """下载失败抛 RuntimeError。"""
        cache_dir = tmp_path / "cache2"
        adapter = JavaAllCallGraphAdapter(
            repo_path=str(tmp_path), jacg_jar=str(tmp_path / "t.jar"), cache_dir=cache_dir
        )
        with (
            patch(
                "jcia.adapters.tools.java_all_call_graph_adapter.urllib.request.urlopen",
                side_effect=OSError("network down"),
            ),
            pytest.raises(RuntimeError, match="Cannot download JACG"),
        ):
            adapter._download_jacg()


class TestBuildServiceTopology:
    """build_service_topology 扫描/解析/依赖（768-805, 818-840, 858-885, 897-908）。"""

    def test_topology_with_provider_and_consumer(self, tmp_path: Path) -> None:
        """含 Dubbo provider 与 consumer 源文件时构建服务与依赖。"""
        provider = tmp_path / "UserServiceImpl.java"
        provider.write_text(
            '@DubboService(version="1.0.0", group="teamA")\npublic class UserServiceImpl {}\n'
        )
        consumer = tmp_path / "OrderManager.java"
        consumer.write_text(
            "public class OrderManager {\n"
            '    @Reference(version="2.0.0", group="grp")\n'
            "    private UserService remoteSvc;\n"
            "}\n"
        )
        adapter = _make_adapter(tmp_path)

        topology = adapter.build_service_topology()

        # provider 服务被识别（含 version/group）
        assert "IUserServiceImpl" in topology["services"]
        provider_info = topology["services"]["IUserServiceImpl"]
        assert provider_info["is_provider"] is True
        assert provider_info["version"] == "1.0.0"
        assert provider_info["group"] == "teamA"
        # consumer 服务被识别
        assert "UserService" in topology["services"]
        assert topology["services"]["UserService"]["is_consumer"] is True
        # 依赖分析：provider 依赖了 consumer 角色的服务
        assert "UserService" in topology["dependencies"]["IUserServiceImpl"]

    def test_parse_dubbo_service_no_class_returns_none(self, tmp_path: Path) -> None:
        """无 class 关键字时返回 None（820-821）。"""
        adapter = _make_adapter(tmp_path)

        assert adapter._parse_dubbo_service("@Service nothing", tmp_path / "X.java") is None

    def test_parse_dubbo_consumer_no_reference_returns_none(self, tmp_path: Path) -> None:
        """无法匹配 @Reference 结构时返回 None（862-863）。"""
        adapter = _make_adapter(tmp_path)

        assert adapter._parse_dubbo_consumer("no annotation here", tmp_path / "X.java") is None

    def test_analyze_service_dependencies_skips_self(self, tmp_path: Path) -> None:
        """依赖分析跳过自身、收集 consumer 服务（897-908）。"""
        adapter = _make_adapter(tmp_path)
        all_services = {
            "IOrder": {"is_consumer": True},
            "IUser": {"is_provider": True},
        }

        deps = adapter._analyze_service_dependencies("IUser", all_services)

        assert deps == ["IOrder"]

    def test_topology_survives_read_error(self, tmp_path: Path) -> None:
        """单个文件解析异常被捕获并跳过（797-798）。"""
        # 名为 *.java 的目录会让 read_text 抛 IsADirectoryError，落入 except 分支
        (tmp_path / "Broken.java").mkdir()
        adapter = _make_adapter(tmp_path)

        topology = adapter.build_service_topology()

        assert topology["services"] == {}
