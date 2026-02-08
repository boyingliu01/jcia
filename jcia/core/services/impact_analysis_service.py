"""影响分析领域服务.

协调变更分析和调用链分析，计算代码变更的完整影响范围。
"""

from typing import Any

from jcia.core.entities.change_set import ChangeSet
from jcia.core.entities.impact_graph import (
    ImpactEdge,
    ImpactGraph,
    ImpactNode,
    ImpactSeverity,
    ImpactType,
)
from jcia.core.interfaces.call_chain_analyzer import (
    CallChainAnalyzer,
)


class ImpactAnalysisService:
    """影响分析服务.

    根据变更集合和调用链分析，计算代码变更的影响范围。
    """

    def __init__(self, call_chain_analyzer: CallChainAnalyzer) -> None:
        """初始化服务.

        Args:
            call_chain_analyzer: 调用链分析器
        """
        self._analyzer = call_chain_analyzer

    def analyze(self, change_set: ChangeSet, max_depth: int = 10) -> ImpactGraph:
        """分析变更的影响范围.

        Args:
            change_set: 变更集合
            max_depth: 最大追溯深度

        Returns:
            ImpactGraph: 影响图
        """
        impact_graph = ImpactGraph(
            change_set_id=change_set.from_commit,
        )

        # 收集所有变更的方法
        changed_methods = change_set.changed_methods
        if not changed_methods:
            return impact_graph

        # 为每个变更方法创建直接影响节点
        for method_name in changed_methods:
            class_name = self._extract_class_name(method_name)
            node = ImpactNode(
                method_name=method_name,
                class_name=class_name,
                impact_type=ImpactType.DIRECT,
                severity=self._determine_severity(class_name),
                depth=0,
            )
            impact_graph.add_node(node)
            impact_graph.root_methods.append(method_name)

            # 分析上游调用者
            upstream_graph = self._analyzer.analyze_upstream(method_name, max_depth)
            self._process_call_chain(
                impact_graph, upstream_graph, method_name, "upstream", max_depth
            )

            # 分析下游被调用者
            downstream_graph = self._analyzer.analyze_downstream(method_name, max_depth)
            self._process_call_chain(
                impact_graph, downstream_graph, method_name, "downstream", max_depth
            )

        return impact_graph

    def get_impact_summary(self, impact_graph: ImpactGraph) -> dict[str, Any]:
        """获取影响摘要.

        Args:
            impact_graph: 影响图

        Returns:
            Dict[str, Any]: 影响摘要
        """
        return {
            "total_methods": impact_graph.total_affected_methods,
            "direct_impacts": impact_graph.direct_impact_count,
            "indirect_impacts": impact_graph.indirect_impact_count,
            "affected_classes": len(impact_graph.affected_classes),
            "high_severity_count": impact_graph.high_severity_count,
            "affected_test_classes": len(impact_graph.affected_test_classes),
        }

    def filter_by_class(self, impact_graph: ImpactGraph, class_name: str) -> ImpactGraph:
        """按类过滤影响.

        Args:
            impact_graph: 原始影响图
            class_name: 类名（支持部分匹配）

        Returns:
            ImpactGraph: 过滤后的影响图
        """
        filtered = ImpactGraph(
            change_set_id=impact_graph.change_set_id,
        )

        for _method_name, node in impact_graph.nodes.items():
            if class_name in node.class_name:
                filtered.add_node(node)

        # 复制相关的边
        for edge in impact_graph.edges:
            if edge.source in filtered.nodes and edge.target in filtered.nodes:
                filtered.add_edge(edge)

        return filtered

    def get_entry_points(self, impact_graph: ImpactGraph) -> list[str]:
        """获取入口点方法（没有调用者的方法）.

        Args:
            impact_graph: 影响图

        Returns:
            List[str]: 入口点方法列表
        """
        return [name for name, node in impact_graph.nodes.items() if node.is_entry_point]

    def get_leaf_methods(self, impact_graph: ImpactGraph) -> list[str]:
        """获取叶子方法（没有下游调用的方法）.

        Args:
            impact_graph: 影响图

        Returns:
            List[str]: 叶子方法列表
        """
        return [name for name, node in impact_graph.nodes.items() if node.is_leaf]

    def _process_call_chain(
        self,
        impact_graph: ImpactGraph,
        call_chain: Any,
        root_method: str,
        direction: str,
        max_depth: int,
    ) -> None:
        """处理调用链，添加到影响图.

        Args:
            impact_graph: 影响图
            call_chain: 调用链图
            root_method: 根方法名
            direction: 方向（upstream/downstream）
            max_depth: 最大深度
        """
        visited = set()

        def traverse(node: Any, depth: int) -> None:
            if depth > max_depth or node is None:
                return

            method_name = getattr(node, "full_name", None)
            if method_name is None:
                return

            if method_name in visited:
                return
            visited.add(method_name)

            # 跳过根节点（已作为直接影响添加）
            if method_name == root_method:
                pass
            elif method_name not in impact_graph.nodes:
                # 创建间接影响节点
                class_name = getattr(node, "class_name", "")
                impact_node = ImpactNode(
                    method_name=method_name,
                    class_name=class_name,
                    impact_type=ImpactType.INDIRECT,
                    severity=self._determine_severity(class_name),
                    depth=depth,
                )
                impact_graph.add_node(impact_node)

            # 添加边
            if direction == "upstream":
                edge = ImpactEdge(source=method_name, target=root_method)
            else:
                edge = ImpactEdge(source=root_method, target=method_name)
            impact_graph.add_edge(edge)

            # 递归处理子节点
            children = getattr(node, "children", [])
            for child in children:
                traverse(child, depth + 1)

        traverse(call_chain.root, 1)

    def _extract_class_name(self, method_full_name: str) -> str:
        """从方法全限定名中提取类名.

        Args:
            method_full_name: 方法全限定名（如 "com.example.Class.method()"）

        Returns:
            str: 类名
        """
        # 去掉方法签名部分
        if "(" in method_full_name:
            method_full_name = method_full_name.split("(", 1)[0]

        # 提取类名（最后一段为方法名）
        parts = method_full_name.split(".")
        if len(parts) >= 2:
            return ".".join(parts[:-1])
        return ""

    def _determine_severity(self, class_name: str) -> ImpactSeverity:
        """根据类名确定影响严重程度.

        Args:
            class_name: 类名

        Returns:
            ImpactSeverity: 影响严重程度
        """
        class_name_lower = class_name.lower()

        # 高严重程度：核心业务类
        high_keywords = [
            "core",
            "kernel",
            "manager",
            "handler",
            "service",
            "controller",
            "business",
            "domain",
            "entity",
            "repository",
            "dao",
            "mapper",
            "adapter",
        ]
        if any(keyword in class_name_lower for keyword in high_keywords):
            return ImpactSeverity.HIGH

        # 中严重程度：一般业务类
        medium_keywords = [
            "component",
            "processor",
            "builder",
            "factory",
            "provider",
            "helper",
            "util",
            "helper",
        ]
        if any(keyword in class_name_lower for keyword in medium_keywords):
            return ImpactSeverity.MEDIUM

        # 低严重程度：配置、工具、常量类
        low_keywords = [
            "config",
            "constant",
            "enum",
            "dto",
            "vo",
            "pojo",
            "model",
            "exception",
            "error",
            "exception",
        ]
        if any(keyword in class_name_lower for keyword in low_keywords):
            return ImpactSeverity.LOW

        # 默认中等严重程度
        return ImpactSeverity.MEDIUM
