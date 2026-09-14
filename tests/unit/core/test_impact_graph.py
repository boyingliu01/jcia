"""ImpactGraph领域实体单元测试."""

import pytest

from jcia.core.entities.impact_graph import (
    ImpactEdge,
    ImpactGraph,
    ImpactNode,
    ImpactSeverity,
    ImpactType,
)


class TestImpactNode:
    """ImpactNode测试类."""

    def test_is_direct_impact(self) -> None:
        """测试直接影响判断."""
        direct = ImpactNode(
            method_name="com.Service.method",
            class_name="Service",
            impact_type=ImpactType.DIRECT,
        )
        indirect = ImpactNode(
            method_name="com.Service.method2",
            class_name="Service",
            impact_type=ImpactType.INDIRECT,
        )

        assert direct.is_direct_impact is True
        assert indirect.is_direct_impact is False

    def test_is_entry_point(self) -> None:
        """测试入口点判断."""
        entry = ImpactNode(
            method_name="com.Service.entry",
            class_name="Service",
            upstream=[],
        )
        non_entry = ImpactNode(
            method_name="com.Service.nonEntry",
            class_name="Service",
            upstream=["com.Controller.call"],
        )

        assert entry.is_entry_point is True
        assert non_entry.is_entry_point is False

    def test_is_leaf(self) -> None:
        """测试叶子节点判断."""
        leaf = ImpactNode(
            method_name="com.Service.leaf",
            class_name="Service",
            downstream=[],
        )
        non_leaf = ImpactNode(
            method_name="com.Service.nonLeaf",
            class_name="Service",
            downstream=["com.Repository.save"],
        )

        assert leaf.is_leaf is True
        assert non_leaf.is_leaf is False

    def test_full_name(self) -> None:
        """测试全限定名."""
        with_sig = ImpactNode(
            method_name="com.Service.method(String)",
            class_name="Service",
        )
        assert with_sig.full_name == "com.Service.method(String)"


class TestImpactGraph:
    """ImpactGraph测试类."""

    @pytest.fixture
    def sample_graph(self) -> ImpactGraph:
        """创建示例影响图."""
        graph = ImpactGraph(change_set_id="test-123")

        # 添加节点
        root = ImpactNode(
            method_name="com.Service.root",
            class_name="Service",
            impact_type=ImpactType.DIRECT,
            severity=ImpactSeverity.HIGH,
            depth=0,
        )
        child1 = ImpactNode(
            method_name="com.Service.child1",
            class_name="Service",
            impact_type=ImpactType.INDIRECT,
            severity=ImpactSeverity.MEDIUM,
            depth=1,
        )
        child2 = ImpactNode(
            method_name="com.Other.child2",
            class_name="Other",
            impact_type=ImpactType.TRANSITIVE,
            severity=ImpactSeverity.LOW,
            depth=2,
        )

        graph.add_node(root)
        graph.add_node(child1)
        graph.add_node(child2)

        # 添加边
        graph.add_edge(
            ImpactEdge(
                source="com.Service.root",
                target="com.Service.child1",
            )
        )
        graph.add_edge(
            ImpactEdge(
                source="com.Service.child1",
                target="com.Other.child2",
            )
        )

        graph.root_methods = ["com.Service.root"]
        return graph

    def test_total_affected_methods(self, sample_graph: ImpactGraph) -> None:
        """测试总受影响方法数."""
        assert sample_graph.total_affected_methods == 3

    def test_direct_impact_count(self, sample_graph: ImpactGraph) -> None:
        """测试直接影响数."""
        assert sample_graph.direct_impact_count == 1

    def test_indirect_impact_count(self, sample_graph: ImpactGraph) -> None:
        """测试间接影响数."""
        assert sample_graph.indirect_impact_count == 1

    def test_high_severity_count(self, sample_graph: ImpactGraph) -> None:
        """测试高风险数."""
        assert sample_graph.high_severity_count == 1

    def test_affected_classes(self, sample_graph: ImpactGraph) -> None:
        """测试受影响类集合."""
        classes = sample_graph.affected_classes
        assert "Service" in classes
        assert "Other" in classes
        assert len(classes) == 2

    def test_get_node(self, sample_graph: ImpactGraph) -> None:
        """测试获取节点."""
        found = sample_graph.get_node("com.Service.root")
        not_found = sample_graph.get_node("com.NotExist.method")

        assert found is not None
        assert found.class_name == "Service"
        assert not_found is None

    def test_add_node(self) -> None:
        """测试添加节点."""
        graph = ImpactGraph()
        node = ImpactNode(
            method_name="com.Test.method",
            class_name="Test",
        )

        graph.add_node(node)

        assert "com.Test.method" in graph.nodes
        assert graph.nodes["com.Test.method"] == node

    def test_add_edge_updates_relationships(self) -> None:
        """测试添加边更新上下游关系."""
        graph = ImpactGraph()

        parent = ImpactNode(method_name="Parent", class_name="Parent")
        child = ImpactNode(method_name="Child", class_name="Child")

        graph.add_node(parent)
        graph.add_node(child)
        graph.add_edge(ImpactEdge(source="Parent", target="Child"))

        assert "Child" in graph.nodes["Parent"].downstream
        assert "Parent" in graph.nodes["Child"].upstream

    def test_add_edge_prevents_duplicates(self) -> None:
        """重复边不应重复记录上下游关系."""
        graph = ImpactGraph()
        parent = ImpactNode(method_name="Parent", class_name="Parent")
        child = ImpactNode(method_name="Child", class_name="Child")
        graph.add_node(parent)
        graph.add_node(child)

        graph.add_edge(ImpactEdge(source="Parent", target="Child"))
        graph.add_edge(ImpactEdge(source="Parent", target="Child"))

        assert graph.nodes["Parent"].downstream.count("Child") == 1
        assert graph.nodes["Child"].upstream.count("Parent") == 1
        assert len([e for e in graph.edges if e.source == "Parent" and e.target == "Child"]) == 1

    def test_get_downstream_chain(self, sample_graph: ImpactGraph) -> None:
        """测试获取下游调用链."""
        chain = sample_graph.get_downstream_chain("com.Service.root")

        assert "com.Service.child1" in chain
        assert "com.Other.child2" in chain

    def test_get_downstream_chain_order_and_depth(self, sample_graph: ImpactGraph) -> None:
        """验证遍历顺序与深度限制不包含起点."""
        limited = sample_graph.get_downstream_chain("com.Service.root", max_depth=1)
        assert "com.Service.child1" in limited
        assert "com.Other.child2" not in limited
        assert len(limited) == 1

        deep = sample_graph.get_downstream_chain("com.Service.root", max_depth=10)
        assert deep.index("com.Service.child1") < deep.index("com.Other.child2")
        assert "com.Service.root" not in deep

    def test_get_upstream_chain(self, sample_graph: ImpactGraph) -> None:
        """测试获取上游调用链."""
        chain = sample_graph.get_upstream_chain("com.Other.child2")

        assert "com.Service.child1" in chain
        assert "com.Service.root" in chain

    def test_merge(self) -> None:
        """测试合并影响图."""
        graph1 = ImpactGraph(change_set_id="id1")
        graph1.add_node(ImpactNode(method_name="Method1", class_name="Class1"))
        graph1.add_node(ImpactNode(method_name="Method2", class_name="Class1"))

        graph2 = ImpactGraph(change_set_id="id2")
        graph2.add_node(ImpactNode(method_name="Method2", class_name="Class1"))
        graph2.add_node(ImpactNode(method_name="Method3", class_name="Class2"))

        merged = graph1.merge(graph2)

        assert merged.change_set_id == "id1"
        assert merged.total_affected_methods == 3
        assert "Method1" in merged.nodes
        assert "Method2" in merged.nodes
        assert "Method3" in merged.nodes

    def test_to_dict(self, sample_graph: ImpactGraph) -> None:
        """测试转换为字典."""
        data = sample_graph.to_dict()

        assert data["change_set_id"] == "test-123"
        assert data["total_affected_methods"] == 3
        assert data["direct_impact_count"] == 1
        assert data["indirect_impact_count"] == 1
        affected_classes = data["affected_classes"]
        assert isinstance(affected_classes, list) and len(affected_classes) == 2
