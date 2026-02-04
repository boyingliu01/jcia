"""调用链构建领域服务.

基于变更集合和代码分析器构建完整的调用链图。
"""

from typing import Any

from jcia.core.entities.impact_graph import (
    ImpactEdge,
    ImpactGraph,
    ImpactNode,
    ImpactSeverity,
    ImpactType,
)
from jcia.core.interfaces.call_chain_analyzer import (
    CallChainAnalyzer,
    CallChainGraph,
    CallChainNode,
)


class CallChainBuilder:
    """调用链构建服务.

    协调变更分析和调用链分析，构建完整的影响图。
    """

    def __init__(self, call_chain_analyzer: CallChainAnalyzer) -> None:
        """初始化服务.

        Args:
            call_chain_analyzer: 调用链分析器
        """
        self._analyzer = call_chain_analyzer

    def build_from_methods(self, changed_methods: list[str], max_depth: int = 10) -> ImpactGraph:
        """从变更方法列表构建调用链图.

        Args:
            changed_methods: 变更的方法列表
            max_depth: 最大追溯深度

        Returns:
            ImpactGraph: 影响图
        """
        impact_graph = ImpactGraph(change_set_id="current")

        if not changed_methods:
            return impact_graph

        for method in changed_methods:
            # 分析上游调用者
            upstream_graph = self._analyzer.analyze_upstream(method, max_depth)
            self._add_graph_to_impact(impact_graph, upstream_graph, method, "upstream")

            # 分析下游被调用者
            downstream_graph = self._analyzer.analyze_downstream(method, max_depth)
            self._add_graph_to_impact(impact_graph, downstream_graph, method, "downstream")

        return impact_graph

    def merge_impact_graphs(self, graphs: list[ImpactGraph]) -> ImpactGraph:
        """合并多个影响图.

        Args:
            graphs: 影响图列表

        Returns:
            ImpactGraph: 合并后的影响图
        """
        if not graphs:
            return ImpactGraph(change_set_id="merged")

        merged = ImpactGraph(change_set_id="merged")

        for graph in graphs:
            for method_name, node in graph.nodes.items():
                if method_name not in merged.nodes:
                    merged.add_node(node)

            for edge in graph.edges:
                merged.add_edge(edge)

        return merged

    def detect_circular_dependencies(self, impact_graph: ImpactGraph) -> list[list[str]]:
        """检测循环依赖.

        Args:
            impact_graph: 影响图

        Returns:
            List[List[str]]: 循环依赖列表（每个循环是一个方法列表）
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: dict[str, bool] = {}
        path: list[str] = []

        def visit(node: str) -> None:
            """DFS访问节点."""
            visited.add(node)
            rec_stack[node] = True
            path.append(node)

            for edge in impact_graph.edges:
                if edge.source == node and edge.target not in visited:
                    visit(edge.target)
                elif edge.source == node and edge.target in rec_stack and rec_stack[edge.target]:
                    # 找到循环
                    cycle_start = path.index(edge.target)
                    cycle = path[cycle_start:] + [edge.target]
                    if cycle not in cycles:
                        cycles.append(cycle)

            path.pop()
            rec_stack[node] = False

        for node in impact_graph.nodes:
            if node not in visited:
                visit(node)

        return cycles

    def find_critical_paths(
        self, impact_graph: ImpactGraph, top_n: int = 5
    ) -> list[dict[str, Any]]:
        """查找关键路径（影响最多的节点）.

        Args:
            impact_graph: 影响图
            top_n: 返回前N个关键节点

        Returns:
            List[Dict[str, Any]]: 关键节点列表，包含影响统计
        """
        node_impacts: dict[str, int] = {}

        for edge in impact_graph.edges:
            source = edge.source
            node_impacts[source] = node_impacts.get(source, 0) + 1

        # 按影响数排序
        sorted_nodes = sorted(node_impacts.items(), key=lambda x: x[1], reverse=True)[:top_n]

        result: list[dict[str, Any]] = []
        for node_name, impact_count in sorted_nodes:
            node = impact_graph.nodes.get(node_name)
            if node:
                result.append(
                    {
                        "method_name": node_name,
                        "class_name": node.class_name,
                        "impact_count": impact_count,
                        "severity": node.severity.value,
                        "impact_type": node.impact_type.value,
                    }
                )

        return result

    def build_coverage_impact(self, impact_graph: ImpactGraph, test_run: Any) -> ImpactGraph:
        """基于覆盖率数据构建影响图.

        Args:
            impact_graph: 原始影响图
            test_run: 测试运行数据

        Returns:
            ImpactGraph: 增强的影响图（包含覆盖率信息）
        """
        # 这里可以根据测试运行数据增强影响图
        # 例如标记哪些方法在测试中被覆盖
        return impact_graph

    def _add_graph_to_impact(
        self,
        impact_graph: ImpactGraph,
        call_chain: CallChainGraph,
        root_method: str,
        direction: str,
    ) -> None:
        """将调用链添加到影响图.

        Args:
            impact_graph: 影响图
            call_chain: 调用链图
            root_method: 根方法名
            direction: 方向（upstream/downstream）
        """
        visited = set()

        def traverse(node: CallChainNode, depth: int) -> None:
            """递归遍历调用链."""
            if node is None:
                return

            method_name = node.full_name
            if method_name in visited:
                return
            visited.add(method_name)

            # 跳过根节点，避免重复
            if method_name != root_method and method_name not in impact_graph.nodes:
                impact_node = ImpactNode(
                    method_name=method_name,
                    class_name=node.class_name,
                    impact_type=ImpactType.INDIRECT,
                    severity=self._determine_severity(node.class_name),
                    depth=depth,
                )
                impact_graph.add_node(impact_node)

            # 添加边
            if direction == "upstream" and method_name != root_method:
                edge = ImpactEdge(source=method_name, target=root_method)
                impact_graph.add_edge(edge)
            elif direction == "downstream" and method_name != root_method:
                edge = ImpactEdge(source=root_method, target=method_name)
                impact_graph.add_edge(edge)

            # 递归处理子节点
            for child in node.children:
                traverse(child, depth + 1)

        traverse(call_chain.root, 1)

    def _determine_severity(self, class_name: str) -> ImpactSeverity:
        """根据类名确定影响严重程度.

        Args:
            class_name: 类名

        Returns:
            ImpactSeverity: 影响严重程度
        """
        class_name_lower = class_name.lower()

        # 核心类标记
        core_keywords = ["core", "kernel", "manager", "handler", "controller"]
        if any(keyword in class_name_lower for keyword in core_keywords):
            return ImpactSeverity.HIGH

        # 工具类或配置类
        if "util" in class_name_lower or "config" in class_name_lower:
            return ImpactSeverity.LOW

        return ImpactSeverity.MEDIUM
