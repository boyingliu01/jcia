"""CallChainBuilder 单元测试."""

from unittest.mock import MagicMock

from jcia.core.entities.impact_graph import ImpactGraph, ImpactNode, ImpactType
from jcia.core.interfaces.call_chain_analyzer import (
    CallChainAnalyzer,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)


class TestCallChainBuilder:
    """CallChainBuilder测试类."""

    def test_build_from_change_set(self) -> None:
        """测试从变更集合构建调用链."""
        # Arrange
        from jcia.core.services.call_chain_builder import CallChainBuilder

        analyzer = MagicMock(spec=CallChainAnalyzer)
        builder = CallChainBuilder(analyzer)

        analyzer.analyze_upstream.return_value = CallChainGraph(
            root=CallChainNode(class_name="Test", method_name="test"),
            direction=CallChainDirection.UPSTREAM,
            max_depth=10,
        )
        analyzer.analyze_downstream.return_value = CallChainGraph(
            root=CallChainNode(class_name="Test", method_name="test"),
            direction=CallChainDirection.DOWNSTREAM,
            max_depth=10,
        )

        # Act
        changed_methods = ["com.example.Service.method()"]
        result = builder.build_from_methods(changed_methods)

        # Assert
        assert result is not None
        analyzer.analyze_upstream.assert_called()
        analyzer.analyze_downstream.assert_called()

    def test_build_empty_methods_returns_empty_graph(self) -> None:
        """测试空方法列表返回空图."""
        from jcia.core.services.call_chain_builder import CallChainBuilder

        analyzer = MagicMock(spec=CallChainAnalyzer)
        builder = CallChainBuilder(analyzer)

        # Act
        result = builder.build_from_methods([])

        # Assert
        assert result.total_affected_methods == 0

    def test_merge_multiple_graphs(self) -> None:
        """测试合并多个调用链图."""
        from jcia.core.services.call_chain_builder import CallChainBuilder

        analyzer = MagicMock(spec=CallChainAnalyzer)
        builder = CallChainBuilder(analyzer)

        # Create two graphs with different nodes
        graph1 = ImpactGraph(change_set_id="commit1")
        graph1.add_node(ImpactNode(method_name="method1", class_name="Class1"))
        graph1.add_node(ImpactNode(method_name="method2", class_name="Class2"))

        graph2 = ImpactGraph(change_set_id="commit2")
        graph2.add_node(ImpactNode(method_name="method3", class_name="Class3"))

        # Act
        result = builder.merge_impact_graphs([graph1, graph2])

        # Assert
        assert result.total_affected_methods == 3

    def test_get_circular_dependencies(self) -> None:
        """测试检测循环依赖."""
        from jcia.core.services.call_chain_builder import CallChainBuilder

        analyzer = MagicMock(spec=CallChainAnalyzer)
        builder = CallChainBuilder(analyzer)

        graph = ImpactGraph(change_set_id="test")
        node1 = ImpactNode(method_name="method1", class_name="Class1")
        node2 = ImpactNode(method_name="method2", class_name="Class2")
        node3 = ImpactNode(method_name="method3", class_name="Class3")

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)

        # Add edges creating a cycle
        from jcia.core.entities.impact_graph import ImpactEdge

        graph.add_edge(ImpactEdge(source="method1", target="method2"))
        graph.add_edge(ImpactEdge(source="method2", target="method3"))
        graph.add_edge(ImpactEdge(source="method3", target="method1"))  # Cycle

        # Act
        cycles = builder.detect_circular_dependencies(graph)

        # Assert
        assert len(cycles) > 0

    def test_find_critical_paths(self) -> None:
        """测试查找关键路径（影响最多节点的方法）."""
        from jcia.core.services.call_chain_builder import CallChainBuilder

        analyzer = MagicMock(spec=CallChainAnalyzer)
        builder = CallChainBuilder(analyzer)

        graph = ImpactGraph(change_set_id="test")

        # Add nodes with different impact levels
        node_high = ImpactNode(
            method_name="highImpact", class_name="Core", impact_type=ImpactType.DIRECT
        )
        node_medium = ImpactNode(
            method_name="mediumImpact", class_name="Service", impact_type=ImpactType.INDIRECT
        )
        node_low = ImpactNode(
            method_name="lowImpact", class_name="Util", impact_type=ImpactType.INDIRECT
        )

        graph.add_node(node_high)
        graph.add_node(node_medium)
        graph.add_node(node_low)

        # Act
        critical = builder.find_critical_paths(graph, top_n=1)

        # Assert
        assert len(critical) <= 1
