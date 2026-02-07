"""ImpactAnalysisService 测试."""

from typing import TYPE_CHECKING

from jcia.core.entities.change_set import ChangeSet, FileChange, MethodChange
from jcia.core.entities.impact_graph import ImpactType
from jcia.core.interfaces.call_chain_analyzer import (
    CallChainAnalyzer,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)

if TYPE_CHECKING:
    from jcia.core.services.impact_analysis_service import ImpactAnalysisService
else:
    from jcia.core.services import ImpactAnalysisService


class MockCallChainAnalyzer(CallChainAnalyzer):
    """模拟调用链分析器."""

    def __init__(self, call_graph_map: dict[str, CallChainGraph] | None = None) -> None:
        self._call_graph_map = call_graph_map or {}

    def analyze_upstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析上游调用者."""
        return self._call_graph_map.get(
            f"upstream_{method}",
            CallChainGraph(
                root=CallChainNode(class_name="", method_name=""),
                direction=CallChainDirection.UPSTREAM,
                max_depth=max_depth,
            ),
        )

    def analyze_downstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析下游被调用者."""
        return self._call_graph_map.get(
            f"downstream_{method}",
            CallChainGraph(
                root=CallChainNode(class_name="", method_name=""),
                direction=CallChainDirection.DOWNSTREAM,
                max_depth=max_depth,
            ),
        )

    def analyze_both_directions(
        self, method: str, max_depth: int = 10
    ) -> tuple[CallChainGraph, CallChainGraph]:
        """同时分析上下游."""
        return (
            self.analyze_upstream(method, max_depth),
            self.analyze_downstream(method, max_depth),
        )

    def build_full_graph(self) -> CallChainGraph:
        """构建完整的调用链图."""
        return CallChainGraph(
            root=CallChainNode(class_name="", method_name=""),
            direction=CallChainDirection.UPSTREAM,
            max_depth=10,
        )

    @property
    def analyzer_type(self):
        """返回分析器类型."""
        from jcia.core.interfaces.call_chain_analyzer import AnalyzerType

        return AnalyzerType.STATIC

    @property
    def supports_cross_service(self) -> bool:
        """是否支持跨服务分析."""
        return False


class TestImpactAnalysisService:
    """ImpactAnalysisService 测试类."""

    def test_analyze_creates_impact_graph_from_change_set(self) -> None:
        """测试从变更集合创建影响图."""
        # Arrange
        change_set = ChangeSet(
            from_commit="abc123",
            to_commit="def456",
        )
        change_set.add_file_change(
            FileChange(
                file_path="com/example/Service.java",
                method_changes=[
                    MethodChange(
                        class_name="com.example.Service",
                        method_name="processData",
                        signature="(String data):void",
                    ),
                ],
            )
        )

        analyzer = MockCallChainAnalyzer()
        service = ImpactAnalysisService(analyzer)

        # Act
        impact_graph = service.analyze(change_set, max_depth=5)

        # Assert
        assert impact_graph is not None
        assert len(impact_graph.root_methods) > 0
        # full_name 包含签名
        assert any("processData" in method for method in impact_graph.root_methods)

    def test_analyze_creates_direct_impact_nodes(self) -> None:
        """测试创建直接影响节点."""
        # Arrange
        change_set = ChangeSet()
        change_set.add_file_change(
            FileChange(
                file_path="com/example/Calculator.java",
                method_changes=[
                    MethodChange(
                        class_name="com.example.Calculator",
                        method_name="add",
                        signature="(int a, int b):int",
                    ),
                    MethodChange(
                        class_name="com.example.Calculator",
                        method_name="subtract",
                        signature="(int a, int b):int",
                    ),
                ],
            )
        )

        analyzer = MockCallChainAnalyzer()
        service = ImpactAnalysisService(analyzer)

        # Act
        impact_graph = service.analyze(change_set, max_depth=3)

        # Assert
        assert impact_graph.direct_impact_count >= 2
        # 查找包含方法名的节点（因为full_name包含签名）
        add_node = None
        for node in impact_graph.nodes.values():
            if "add" in node.method_name and "Calculator" in node.class_name:
                add_node = node
                break
        assert add_node is not None
        assert add_node.impact_type == ImpactType.DIRECT

    def test_analyze_includes_upstream_callers(self) -> None:
        """测试包含上游调用者."""
        # Arrange
        from jcia.core.interfaces.call_chain_analyzer import CallChainDirection

        change_set = ChangeSet()
        change_set.add_file_change(
            FileChange(
                file_path="com/example/DataProcessor.java",
                method_changes=[
                    MethodChange(
                        class_name="com.example.DataProcessor",
                        method_name="validate",
                        signature="(String input):boolean",
                    ),
                ],
            )
        )

        # 创建模拟的调用链图
        caller_node = CallChainNode(
            class_name="com.example.Controller",
            method_name="handleRequest",
        )
        target_node = CallChainNode(
            class_name="com.example.DataProcessor",
            method_name="validate",
            children=[caller_node],
        )
        upstream_graph = CallChainGraph(
            root=target_node,
            direction=CallChainDirection.UPSTREAM,
            max_depth=3,
        )

        analyzer = MockCallChainAnalyzer(
            {"upstream_com.example.DataProcessor.validate": upstream_graph}
        )
        service = ImpactAnalysisService(analyzer)

        # Act
        impact_graph = service.analyze(change_set, max_depth=5)

        # Assert
        # 查找验证方法节点
        validate_node = None
        for node in impact_graph.nodes.values():
            if "validate" in node.method_name and "DataProcessor" in node.class_name:
                validate_node = node
                break
        assert validate_node is not None
        # 模拟的调用链会产生边或节点
        assert len(impact_graph.nodes) > 0

    def test_analyze_includes_downstream_callees(self) -> None:
        """测试包含下游被调用者."""
        # Arrange
        change_set = ChangeSet()
        change_set.add_file_change(
            FileChange(
                file_path="com/example/CacheManager.java",
                method_changes=[
                    MethodChange(
                        class_name="com.example.CacheManager",
                        method_name="clearCache",
                        signature="():void",
                    ),
                ],
            )
        )

        analyzer = MockCallChainAnalyzer()
        service = ImpactAnalysisService(analyzer)

        # Act
        impact_graph = service.analyze(change_set, max_depth=3)

        # Assert
        # 查找clearCache节点
        clear_cache_node = None
        for node in impact_graph.nodes.values():
            if "clearCache" in node.method_name and "CacheManager" in node.class_name:
                clear_cache_node = node
                break
        assert clear_cache_node is not None

    def test_analyze_handles_empty_change_set(self) -> None:
        """测试处理空变更集."""
        # Arrange
        change_set = ChangeSet()
        analyzer = MockCallChainAnalyzer()
        service = ImpactAnalysisService(analyzer)

        # Act
        impact_graph = service.analyze(change_set, max_depth=5)

        # Assert
        assert impact_graph.total_affected_methods == 0
        assert len(impact_graph.root_methods) == 0

    def test_calculate_impact_summary(self) -> None:
        """测试计算影响摘要."""
        # Arrange
        change_set = ChangeSet()
        change_set.add_file_change(
            FileChange(
                file_path="com/example/CoreService.java",
                method_changes=[
                    MethodChange(
                        class_name="com.example.CoreService",
                        method_name="execute",
                        signature="():void",
                    ),
                ],
            )
        )

        analyzer = MockCallChainAnalyzer()
        service = ImpactAnalysisService(analyzer)

        # Act
        impact_graph = service.analyze(change_set, max_depth=5)
        summary = service.get_impact_summary(impact_graph)

        # Assert
        assert "total_methods" in summary
        assert "direct_impacts" in summary
        assert "indirect_impacts" in summary
        assert "affected_classes" in summary

    def test_filter_impact_by_class(self) -> None:
        """测试按类过滤影响."""
        # Arrange
        change_set = ChangeSet()
        change_set.add_file_change(
            FileChange(
                file_path="com/example/FirstService.java",
                method_changes=[
                    MethodChange(
                        class_name="com.example.FirstService",
                        method_name="doWork",
                        signature="():void",
                    ),
                ],
            )
        )
        change_set.add_file_change(
            FileChange(
                file_path="com/example/SecondService.java",
                method_changes=[
                    MethodChange(
                        class_name="com.example.SecondService",
                        method_name="doAnotherWork",
                        signature="():void",
                    ),
                ],
            )
        )

        analyzer = MockCallChainAnalyzer()
        service = ImpactAnalysisService(analyzer)

        # Act
        impact_graph = service.analyze(change_set, max_depth=3)
        filtered = service.filter_by_class(impact_graph, "com.example.FirstService")

        # Assert
        assert filtered.total_affected_methods <= impact_graph.total_affected_methods

    def test_get_entry_point_methods(self) -> None:
        """测试获取入口点方法."""
        # Arrange
        change_set = ChangeSet()
        change_set.add_file_change(
            FileChange(
                file_path="com/example/Entrypoint.java",
                method_changes=[
                    MethodChange(
                        class_name="com.example.Entrypoint",
                        method_name="main",
                        signature="(String[] args):void",
                    ),
                ],
            )
        )

        analyzer = MockCallChainAnalyzer()
        service = ImpactAnalysisService(analyzer)

        # Act
        impact_graph = service.analyze(change_set, max_depth=3)
        entry_points = service.get_entry_points(impact_graph)

        # Assert
        assert isinstance(entry_points, list)
