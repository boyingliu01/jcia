"""影响图领域实体.

表示代码变更的影响范围，包含调用链和影响方法。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ImpactType(Enum):
    """影响类型枚举."""

    DIRECT = "direct"  # 直接影响
    INDIRECT = "indirect"  # 间接影响
    TRANSITIVE = "transitive"  # 传递影响


class ImpactSeverity(Enum):
    """影响严重程度枚举."""

    HIGH = "high"  # 高风险（核心方法）
    MEDIUM = "medium"  # 中风险
    LOW = "low"  # 低风险


@dataclass
class ImpactNode:
    """影响图节点.

    Attributes:
        method_name: 方法全限定名
        class_name: 类名
        impact_type: 影响类型
        severity: 严重程度
        depth: 影响深度（距离变更点的距离）
        upstream: 上游调用者
        downstream: 下游被调用者
        metadata: 额外元数据
    """

    method_name: str
    class_name: str
    impact_type: ImpactType = ImpactType.DIRECT
    severity: ImpactSeverity = ImpactSeverity.MEDIUM
    depth: int = 0
    upstream: list[str] = field(default_factory=list)
    downstream: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_direct_impact(self) -> bool:
        """是否是直接影响."""
        return self.impact_type == ImpactType.DIRECT

    @property
    def is_entry_point(self) -> bool:
        """是否是入口点（没有其他调用者）."""
        return len(self.upstream) == 0

    @property
    def is_leaf(self) -> bool:
        """是否是叶子节点（没有下游调用）."""
        return len(self.downstream) == 0

    @property
    def full_name(self) -> str:
        """获取方法全限定名."""
        return self.method_name


@dataclass
class ImpactEdge:
    """影响图边.

    表示方法间的调用关系。

    Attributes:
        source: 源方法
        target: 目标方法
        call_type: 调用类型（invokevirtual, invokestatic等）
        line_number: 调用行号
    """

    source: str
    target: str
    call_type: str | None = None
    line_number: int = 0


@dataclass
class ImpactGraph:
    """影响图.

    表示代码变更的完整影响范围。

    Attributes:
        change_set_id: 关联的变更集标识
        nodes: 影响节点映射（方法名->节点）
        edges: 影响边列表
        root_methods: 根方法（变更点）
    """

    change_set_id: str | None = None
    nodes: dict[str, ImpactNode] = field(default_factory=dict)
    edges: list[ImpactEdge] = field(default_factory=list)
    root_methods: list[str] = field(default_factory=list)

    @property
    def total_affected_methods(self) -> int:
        """总受影响方法数."""
        return len(self.nodes)

    @property
    def direct_impact_count(self) -> int:
        """直接影响方法数."""
        return sum(1 for node in self.nodes.values() if node.impact_type == ImpactType.DIRECT)

    @property
    def indirect_impact_count(self) -> int:
        """间接影响方法数."""
        return sum(1 for node in self.nodes.values() if node.impact_type == ImpactType.INDIRECT)

    @property
    def high_severity_count(self) -> int:
        """高风险方法数."""
        return sum(1 for node in self.nodes.values() if node.severity == ImpactSeverity.HIGH)

    @property
    def affected_classes(self) -> set[str]:
        """受影响的类集合."""
        return {node.class_name for node in self.nodes.values()}

    @property
    def affected_test_classes(self) -> set[str]:
        """受影响的测试类集合."""
        return {
            node.class_name
            for node in self.nodes.values()
            if "Test" in node.class_name or "test" in node.class_name.lower()
        }

    def add_node(self, node: ImpactNode) -> None:
        """添加影响节点.

        Args:
            node: 影响节点
        """
        self.nodes[node.method_name] = node

    def add_edge(self, edge: ImpactEdge) -> None:
        """添加影响边（避免重复）.

        Args:
            edge: 影响边
        """
        if edge in self.edges:
            return

        self.edges.append(edge)

        # 更新节点的上下游关系，避免重复记录
        if edge.source in self.nodes and edge.target not in self.nodes[edge.source].downstream:
            self.nodes[edge.source].downstream.append(edge.target)
        if edge.target in self.nodes and edge.source not in self.nodes[edge.target].upstream:
            self.nodes[edge.target].upstream.append(edge.source)

    def get_node(self, method_name: str) -> ImpactNode | None:
        """获取指定方法的影响节点.

        Args:
            method_name: 方法全限定名

        Returns:
            Optional[ImpactNode]: 影响节点
        """
        return self.nodes.get(method_name)

    def get_upstream_chain(self, method_name: str, max_depth: int = 10) -> list[str]:
        """获取上游调用链.

        Args:
            method_name: 起始方法
            max_depth: 最大深度

        Returns:
            List[str]: 上游方法列表
        """
        chain = []
        visited = set()

        def traverse(method: str, depth: int) -> None:
            if depth > max_depth or method in visited:
                return
            visited.add(method)

            node = self.nodes.get(method)
            if node:
                for upstream in node.upstream:
                    next_depth = depth + 1
                    if next_depth > max_depth:
                        continue
                    if upstream not in chain:
                        chain.append(upstream)
                    traverse(upstream, next_depth)

        traverse(method_name, 0)
        return chain

    def get_downstream_chain(self, method_name: str, max_depth: int = 10) -> list[str]:
        """获取下游调用链.

        Args:
            method_name: 起始方法
            max_depth: 最大深度

        Returns:
            List[str]: 下游方法列表
        """
        chain = []
        visited = set()

        def traverse(method: str, depth: int) -> None:
            if depth > max_depth or method in visited:
                return
            visited.add(method)

            node = self.nodes.get(method)
            if node:
                for downstream in node.downstream:
                    next_depth = depth + 1
                    if next_depth > max_depth:
                        continue
                    if downstream not in chain:
                        chain.append(downstream)
                    traverse(downstream, next_depth)

        traverse(method_name, 0)
        return chain

    def merge(self, other: "ImpactGraph") -> "ImpactGraph":
        """合并另一个影响图.

        Args:
            other: 另一个影响图

        Returns:
            ImpactGraph: 合并后的影响图
        """
        merged = ImpactGraph(
            change_set_id=self.change_set_id or other.change_set_id,
            root_methods=list(set(self.root_methods + other.root_methods)),
        )

        # 合并节点
        for _method, node in self.nodes.items():
            merged.add_node(node)
        for _method, node in other.nodes.items():
            if _method not in merged.nodes:
                merged.add_node(node)

        # 合并边
        for edge in self.edges:
            merged.add_edge(edge)
        for edge in other.edges:
            if edge not in merged.edges:
                merged.add_edge(edge)

        return merged

    def to_dict(self) -> dict[str, object]:
        """转换为字典."""
        return {
            "change_set_id": self.change_set_id,
            "total_affected_methods": self.total_affected_methods,
            "direct_impact_count": self.direct_impact_count,
            "indirect_impact_count": self.indirect_impact_count,
            "high_severity_count": self.high_severity_count,
            "affected_classes": list(self.affected_classes),
            "root_methods": self.root_methods,
            "nodes": [
                {
                    "method_name": node.method_name,
                    "class_name": node.class_name,
                    "impact_type": node.impact_type.value,
                    "severity": node.severity.value,
                    "depth": node.depth,
                }
                for node in self.nodes.values()
            ],
        }
