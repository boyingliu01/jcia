"""MockCallChainAnalyzer 单元测试."""

from pathlib import Path

import pytest

from jcia.adapters.tools.mock_call_chain_analyzer import MockCallChainAnalyzer
from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainDirection,
)


@pytest.fixture
def mock_analyzer(tmp_path: Path) -> MockCallChainAnalyzer:
    """创建 Mock 分析器实例."""
    return MockCallChainAnalyzer(repo_path=str(tmp_path))


class TestMockCallChainAnalyzer:
    """MockCallChainAnalyzer 测试类."""

    def test_init(self, tmp_path: Path) -> None:
        """测试初始化."""
        analyzer = MockCallChainAnalyzer(repo_path=str(tmp_path))

        assert analyzer._repo_path == str(tmp_path)

    def test_analyzer_type_returns_hybrid(self, mock_analyzer: MockCallChainAnalyzer) -> None:
        """测试分析器类型返回 HYBRID."""
        assert mock_analyzer.analyzer_type == AnalyzerType.HYBRID

    def test_supports_cross_service_returns_false(
        self, mock_analyzer: MockCallChainAnalyzer
    ) -> None:
        """测试跨服务支持返回 False."""
        assert mock_analyzer.supports_cross_service is False

    def test_analyze_upstream_returns_graph(self, mock_analyzer: MockCallChainAnalyzer) -> None:
        """测试上游分析返回图."""
        graph = mock_analyzer.analyze_upstream("com.example.Service.method1", max_depth=5)

        assert graph is not None
        assert graph.direction == CallChainDirection.BOTH
        assert graph.max_depth == 5
        assert graph.root.method_name == "method1"
        assert graph.root.class_name == "com.example.Service"

    def test_analyze_downstream_returns_graph(
        self, mock_analyzer: MockCallChainAnalyzer
    ) -> None:
        """测试下游分析返回图."""
        graph = mock_analyzer.analyze_downstream("Service.method", max_depth=10)

        assert graph is not None
        assert graph.root.method_name == "method"
        assert graph.root.class_name == "Service"

    def test_analyze_both_directions_returns_tuple(
        self, mock_analyzer: MockCallChainAnalyzer
    ) -> None:
        """测试双向分析返回元组."""
        upstream, downstream = mock_analyzer.analyze_both_directions(
            "TestClass.testMethod", max_depth=8
        )

        assert upstream is not None
        assert downstream is not None
        assert upstream.root.method_name == "testMethod"
        assert downstream.root.method_name == "testMethod"

    def test_build_full_graph_returns_graph(self, mock_analyzer: MockCallChainAnalyzer) -> None:
        """测试构建完整图返回图."""
        graph = mock_analyzer.build_full_graph()

        assert graph is not None
        assert graph.root.method_name == "root"

    def test_create_empty_graph_with_simple_method(
        self, mock_analyzer: MockCallChainAnalyzer
    ) -> None:
        """测试使用简单方法名创建空图."""
        graph = mock_analyzer._create_empty_graph("simpleMethod", max_depth=5)

        assert graph.root.method_name == "simpleMethod"
        assert graph.root.class_name == ""

    def test_create_empty_graph_with_full_qualified_name(
        self, mock_analyzer: MockCallChainAnalyzer
    ) -> None:
        """测试使用全限定名创建空图."""
        graph = mock_analyzer._create_empty_graph(
            "com.example.service.UserService.getUser", max_depth=10
        )

        assert graph.root.method_name == "getUser"
        assert graph.root.class_name == "com.example.service.UserService"

    def test_graph_total_nodes_is_one(self, mock_analyzer: MockCallChainAnalyzer) -> None:
        """测试图的节点总数为 1（只有根节点）."""
        graph = mock_analyzer.analyze_upstream("method")

        assert graph.total_nodes == 1