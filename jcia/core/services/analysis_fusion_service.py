"""分析结果融合服务.

将多个分析器的结果进行融合，包括静态分析、动态分析和覆盖率数据，
使用贝叶斯方法计算后验概率，提高分析精度。
"""

import logging

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
)

logger = logging.getLogger(__name__)


class FusionStrategy:
    """融合策略枚举."""

    BAYESIAN = "bayesian"
    VOTING = "voting"
    WEIGHTED = "weighted"
    UNION = "union"
    INTERSECTION = "intersection"


class AnalysisFusionService:
    """分析结果融合服务.

    支持多种融合策略：贝叶斯、投票、加权、并集、交集。
    融合静态分析和动态分析的结果，考虑测试覆盖率数据，
    使用贝叶斯方法计算后验概率。
    """

    def __init__(
        self,
        static_analyzer: CallChainAnalyzer | None = None,
        dynamic_analyzer: CallChainAnalyzer | None = None,
        coverage_data: dict[str, float] | None = None,
    ) -> None:
        """初始化融合服务.

        Args:
            static_analyzer: 静态分析器
            dynamic_analyzer: 动态分析器
            coverage_data: 覆盖率数据（方法名->覆盖率）
        """
        self._static_analyzer = static_analyzer
        self._dynamic_analyzer = dynamic_analyzer
        self._coverage_data = coverage_data or {}

        coverage_count = len(self._coverage_data)
        logger.info(
            f"AnalysisFusionService initialized with "
            f"static={bool(static_analyzer)}, dynamic={bool(dynamic_analyzer)}, "
            f"coverage={coverage_count} methods"
        )

    def fuse_upstream(
        self,
        method: str,
        max_depth: int = 10,
        strategy: str = FusionStrategy.BAYESIAN,
    ) -> ImpactGraph:
        """融合上游调用链分析结果.

        Args:
            method: 起始方法全限定名
            max_depth: 最大追溯深度
            strategy: 融合策略（贝叶斯、投票、加权、并集、交集）

        Returns:
            ImpactGraph: 融合后的影响图
        """
        static_graph = None
        dynamic_graph = None

        if self._static_analyzer:
            try:
                static_graph = self._static_analyzer.analyze_upstream(method, max_depth)
            except Exception as e:
                logger.warning(f"Static analysis failed: {e}")

        if self._dynamic_analyzer:
            try:
                dynamic_graph = self._dynamic_analyzer.analyze_upstream(method, max_depth)
            except Exception as e:
                logger.warning(f"Dynamic analysis failed: {e}")

        if strategy == FusionStrategy.BAYESIAN:
            return self._bayesian_fusion_upstream(method, static_graph, dynamic_graph, max_depth)
        elif strategy == FusionStrategy.VOTING:
            return self._voting_fusion_upstream(method, static_graph, dynamic_graph, max_depth)
        elif strategy == FusionStrategy.WEIGHTED:
            return self._weighted_fusion_upstream(method, static_graph, dynamic_graph, max_depth)
        elif strategy == FusionStrategy.UNION:
            return self._union_fusion_upstream(method, static_graph, dynamic_graph, max_depth)
        elif strategy == FusionStrategy.INTERSECTION:
            return self._intersection_fusion_upstream(
                method, static_graph, dynamic_graph, max_depth
            )
        else:
            return self._bayesian_fusion_upstream(method, static_graph, dynamic_graph, max_depth)

    def fuse_downstream(
        self,
        method: str,
        max_depth: int = 10,
        strategy: str = FusionStrategy.BAYESIAN,
    ) -> ImpactGraph:
        """融合下游调用链分析结果.

        Args:
            method: 起始方法全限定名
            max_depth: 最大追溯深度
            strategy: 融合策略（贝叶斯、投票、加权、并集、交集）

        Returns:
            ImpactGraph: 融合后的影响图
        """
        static_graph = None
        dynamic_graph = None

        if self._static_analyzer:
            try:
                static_graph = self._static_analyzer.analyze_downstream(method, max_depth)
            except Exception as e:
                logger.warning(f"Static analysis failed: {e}")

        if self._dynamic_analyzer:
            try:
                dynamic_graph = self._dynamic_analyzer.analyze_downstream(method, max_depth)
            except Exception as e:
                logger.warning(f"Dynamic analysis failed: {e}")

        if strategy == FusionStrategy.BAYESIAN:
            return self._bayesian_fusion_downstream(method, static_graph, dynamic_graph, max_depth)
        elif strategy == FusionStrategy.VOTING:
            return self._voting_fusion_downstream(method, static_graph, dynamic_graph, max_depth)
        elif strategy == FusionStrategy.WEIGHTED:
            return self._weighted_fusion_downstream(method, static_graph, dynamic_graph, max_depth)
        elif strategy == FusionStrategy.UNION:
            return self._union_fusion_downstream(method, static_graph, dynamic_graph, max_depth)
        elif strategy == FusionStrategy.INTERSECTION:
            return self._intersection_fusion_downstream(
                method, static_graph, dynamic_graph, max_depth
            )
        else:
            return self._bayesian_fusion_downstream(method, static_graph, dynamic_graph, max_depth)

    def _calculate_posterior(self, prior: float, likelihood: float, conditional: float) -> float:
        """计算贝叶斯后验概率.

        使用贝叶斯定理：P(H|E) = P(E|H) * P(H) / P(E)

        Args:
            prior: 先验概率 P(H)
            likelihood: 似然 P(E|H)
            conditional: 条件概率调整因子

        Returns:
            float: 后验概率 (0.0 - 1.0)
        """
        numerator = likelihood * prior * conditional
        denominator = numerator + (1 - likelihood) * (1 - prior)

        if denominator == 0:
            return 0.5

        posterior = numerator / denominator
        return max(0.0, min(1.0, posterior))

    def _create_root_node(self, method: str) -> ImpactNode:
        """创建根影响节点.

        Args:
            method: 方法全限定名

        Returns:
            ImpactNode: 根节点
        """
        class_name, method_name = self._parse_method(method)

        return ImpactNode(
            method_name=method,
            class_name=class_name,
            impact_type=ImpactType.DIRECT,
            severity=ImpactSeverity.HIGH,
            depth=0,
        )

    def _parse_method(self, method: str) -> tuple[str, str]:
        """解析方法全限定名.

        Args:
            method: 方法全限定名（格式：类名.方法名）

        Returns:
            Tuple[str, str]: (类名, 方法名)
        """
        if "." in method:
            parts = method.rsplit(".", 1)
            return parts[0], parts[1]
        return "", method

    def _bayesian_fusion_upstream(
        self,
        method: str,
        static_graph: CallChainGraph | None,
        dynamic_graph: CallChainGraph | None,
        max_depth: int,
    ) -> ImpactGraph:
        """贝叶斯融合上游调用链.

        使用贝叶斯方法融合静态分析和动态分析结果。

        Args:
            method: 起始方法
            static_graph: 静态分析调用链图
            dynamic_graph: 动态分析调用链图
            max_depth: 最大深度

        Returns:
            ImpactGraph: 融合后的影响图
        """
        fused = ImpactGraph(change_set_id=f"fusion_{method}")

        root_node = self._create_root_node(method)
        fused.add_node(root_node)
        fused.root_methods.append(method)

        static_methods = static_graph.get_all_methods() if static_graph else []
        dynamic_methods = dynamic_graph.get_all_methods() if dynamic_graph else []
        all_candidates = set(static_methods + dynamic_methods)

        for candidate in all_candidates:
            prior = 0.5
            if candidate in static_methods:
                prior = 0.8

            likelihood = 0.5
            if dynamic_graph and candidate in dynamic_methods:
                likelihood = 0.95

            conditional = 1.0
            coverage = self._coverage_data.get(candidate, None)
            if coverage is not None:
                if coverage < 0.3:
                    conditional = 1.5
                elif coverage < 0.5:
                    conditional = 1.2
                elif coverage < 0.7:
                    conditional = 1.1

            posterior = self._calculate_posterior(prior, likelihood, conditional)

            if posterior > 0.5:
                node = self._create_fusion_node(
                    candidate, posterior, static_methods, dynamic_methods
                )
                fused.add_node(node)

                edge = ImpactEdge(source=candidate, target=method)
                fused.add_edge(edge)

        return fused

    def _bayesian_fusion_downstream(
        self,
        method: str,
        static_graph: CallChainGraph | None,
        dynamic_graph: CallChainGraph | None,
        max_depth: int,
    ) -> ImpactGraph:
        """贝叶斯融合下游调用链.

        使用贝叶斯方法融合静态分析和动态分析结果。

        Args:
            method: 起始方法
            static_graph: 静态分析调用链图
            dynamic_graph: 动态分析调用链图
            max_depth: 最大深度

        Returns:
            ImpactGraph: 融合后的影响图
        """
        fused = ImpactGraph(change_set_id=f"fusion_{method}")

        root_node = self._create_root_node(method)
        fused.add_node(root_node)
        fused.root_methods.append(method)

        static_methods = static_graph.get_all_methods() if static_graph else []
        dynamic_methods = dynamic_graph.get_all_methods() if dynamic_graph else []
        all_candidates = set(static_methods + dynamic_methods)

        for candidate in all_candidates:
            prior = 0.5
            if candidate in static_methods:
                prior = 0.8

            likelihood = 0.5
            if dynamic_graph and candidate in dynamic_methods:
                likelihood = 0.95

            conditional = 1.0
            coverage = self._coverage_data.get(candidate, None)
            if coverage is not None:
                if coverage < 0.3:
                    conditional = 1.5
                elif coverage < 0.5:
                    conditional = 1.2
                elif coverage < 0.7:
                    conditional = 1.1

            posterior = self._calculate_posterior(prior, likelihood, conditional)

            if posterior > 0.5:
                node = self._create_fusion_node(
                    candidate, posterior, static_methods, dynamic_methods
                )
                fused.add_node(node)

                edge = ImpactEdge(source=method, target=candidate)
                fused.add_edge(edge)

        return fused

    def _create_fusion_node(
        self,
        method: str,
        confidence: float,
        static_methods: list[str],
        dynamic_methods: list[str],
    ) -> ImpactNode:
        """创建融合节点.

        Args:
            method: 方法名
            confidence: 置信度
            static_methods: 静态分析方法列表
            dynamic_methods: 动态分析方法列表

        Returns:
            ImpactNode: 融合节点
        """
        class_name, method_name = self._parse_method(method)

        severity = self._determine_fusion_severity(
            confidence, static_methods, dynamic_methods, method
        )

        impact_type = ImpactType.DIRECT if method in static_methods else ImpactType.INDIRECT

        node = ImpactNode(
            method_name=method,
            class_name=class_name,
            impact_type=impact_type,
            severity=severity,
            depth=1,
            metadata={
                "fusion_confidence": confidence,
                "in_static": method in static_methods,
                "in_dynamic": method in dynamic_methods,
            },
        )

        if method in self._coverage_data:
            node.metadata["coverage"] = self._coverage_data[method]

        return node

    def _determine_fusion_severity(
        self,
        confidence: float,
        static_methods: list[str],
        dynamic_methods: list[str],
        method: str,
    ) -> ImpactSeverity:
        """确定融合严重程度.

        基于置信度、分析方法来源和类名关键词确定严重程度。

        Args:
            confidence: 置信度
            static_methods: 静态分析方法列表
            dynamic_methods: 动态分析方法列表
            method: 方法名

        Returns:
            ImpactSeverity: 严重程度
        """
        class_name, _ = self._parse_method(method)

        score = confidence * 100

        if method in static_methods and method in dynamic_methods:
            score += 30
        elif method in static_methods or method in dynamic_methods:
            score += 10

        keywords_high = ["core", "kernel", "manager", "handler", "controller", "service"]
        keywords_medium = ["util", "config", "helper"]

        for keyword in keywords_high:
            if keyword.lower() in class_name.lower():
                score += 20
                break

        for keyword in keywords_medium:
            if keyword.lower() in class_name.lower():
                score += 10
                break

        if score >= 80:
            return ImpactSeverity.HIGH
        elif score >= 50:
            return ImpactSeverity.MEDIUM
        else:
            return ImpactSeverity.LOW

    # ==================== 投票融合策略 ====================

    def _voting_fusion_upstream(
        self,
        method: str,
        static_graph: CallChainGraph | None,
        dynamic_graph: CallChainGraph | None,
        max_depth: int,
    ) -> ImpactGraph:
        """投票融合上游调用链.

        每个分析器投票，多数同意的结果被保留。

        Args:
            method: 起始方法
            static_graph: 静态分析调用链图
            dynamic_graph: 动态分析调用链图
            max_depth: 最大深度

        Returns:
            ImpactGraph: 融合后的影响图
        """
        fused = ImpactGraph(change_set_id=f"fusion_voting_{method}")

        root_node = self._create_root_node(method)
        fused.add_node(root_node)
        fused.root_methods.append(method)

        static_methods = static_graph.get_all_methods() if static_graph else []
        dynamic_methods = dynamic_graph.get_all_methods() if dynamic_graph else []

        # 投票统计
        all_candidates = set(static_methods + dynamic_methods)
        analyzer_count = sum([1 for a in [static_graph, dynamic_graph] if a is not None])

        for candidate in all_candidates:
            votes = 0
            if candidate in static_methods:
                votes += 1
            if candidate in dynamic_methods:
                votes += 1

            # 多数通过
            if votes >= analyzer_count / 2:
                confidence = votes / analyzer_count if analyzer_count > 0 else 0.5
                node = self._create_fusion_node(
                    candidate, confidence, static_methods, dynamic_methods
                )
                fused.add_node(node)
                edge = ImpactEdge(source=candidate, target=method)
                fused.add_edge(edge)

        return fused

    def _voting_fusion_downstream(
        self,
        method: str,
        static_graph: CallChainGraph | None,
        dynamic_graph: CallChainGraph | None,
        max_depth: int,
    ) -> ImpactGraph:
        """投票融合下游调用链."""
        fused = ImpactGraph(change_set_id=f"fusion_voting_{method}")

        root_node = self._create_root_node(method)
        fused.add_node(root_node)
        fused.root_methods.append(method)

        static_methods = static_graph.get_all_methods() if static_graph else []
        dynamic_methods = dynamic_graph.get_all_methods() if dynamic_graph else []

        all_candidates = set(static_methods + dynamic_methods)
        analyzer_count = sum([1 for a in [static_graph, dynamic_graph] if a is not None])

        for candidate in all_candidates:
            votes = 0
            if candidate in static_methods:
                votes += 1
            if candidate in dynamic_methods:
                votes += 1

            if votes >= analyzer_count / 2:
                confidence = votes / analyzer_count if analyzer_count > 0 else 0.5
                node = self._create_fusion_node(
                    candidate, confidence, static_methods, dynamic_methods
                )
                fused.add_node(node)
                edge = ImpactEdge(source=method, target=candidate)
                fused.add_edge(edge)

        return fused

    # ==================== 加权融合策略 ====================

    def _weighted_fusion_upstream(
        self,
        method: str,
        static_graph: CallChainGraph | None,
        dynamic_graph: CallChainGraph | None,
        max_depth: int,
    ) -> ImpactGraph:
        """加权融合上游调用链.

        为不同分析器分配权重，加权融合结果。
        静态分析器通常权重较高，动态分析器根据覆盖率调整。

        Args:
            method: 起始方法
            static_graph: 静态分析调用链图
            dynamic_graph: 动态分析调用链图
            max_depth: 最大深度

        Returns:
            ImpactGraph: 融合后的影响图
        """
        fused = ImpactGraph(change_set_id=f"fusion_weighted_{method}")

        root_node = self._create_root_node(method)
        fused.add_node(root_node)
        fused.root_methods.append(method)

        static_methods = static_graph.get_all_methods() if static_graph else []
        dynamic_methods = dynamic_graph.get_all_methods() if dynamic_graph else []

        # 计算分析器权重
        static_weight = 0.6 if static_graph else 0.0
        dynamic_weight = 0.4 if dynamic_graph else 0.0

        # 根据覆盖率调整动态分析权重
        if dynamic_graph and self._coverage_data:
            avg_coverage = (
                sum(self._coverage_data.values()) / len(self._coverage_data)
                if self._coverage_data
                else 0
            )
            if avg_coverage > 0.7:
                dynamic_weight = 0.5
                static_weight = 0.5

        # 归一化权重
        total_weight = static_weight + dynamic_weight
        if total_weight > 0:
            static_weight /= total_weight
            dynamic_weight /= total_weight

        all_candidates = set(static_methods + dynamic_methods)

        for candidate in all_candidates:
            # 计算加权置信度
            confidence = 0.0
            if candidate in static_methods:
                confidence += static_weight * 0.8
            if candidate in dynamic_methods:
                confidence += dynamic_weight * 0.95

            if confidence > 0.3:  # 阈值
                node = self._create_fusion_node(
                    candidate, confidence, static_methods, dynamic_methods
                )
                fused.add_node(node)
                edge = ImpactEdge(source=candidate, target=method)
                fused.add_edge(edge)

        return fused

    def _weighted_fusion_downstream(
        self,
        method: str,
        static_graph: CallChainGraph | None,
        dynamic_graph: CallChainGraph | None,
        max_depth: int,
    ) -> ImpactGraph:
        """加权融合下游调用链."""
        fused = ImpactGraph(change_set_id=f"fusion_weighted_{method}")

        root_node = self._create_root_node(method)
        fused.add_node(root_node)
        fused.root_methods.append(method)

        static_methods = static_graph.get_all_methods() if static_graph else []
        dynamic_methods = dynamic_graph.get_all_methods() if dynamic_graph else []

        static_weight = 0.6 if static_graph else 0.0
        dynamic_weight = 0.4 if dynamic_graph else 0.0

        if dynamic_graph and self._coverage_data:
            avg_coverage = (
                sum(self._coverage_data.values()) / len(self._coverage_data)
                if self._coverage_data
                else 0
            )
            if avg_coverage > 0.7:
                dynamic_weight = 0.5
                static_weight = 0.5

        total_weight = static_weight + dynamic_weight
        if total_weight > 0:
            static_weight /= total_weight
            dynamic_weight /= total_weight

        all_candidates = set(static_methods + dynamic_methods)

        for candidate in all_candidates:
            confidence = 0.0
            if candidate in static_methods:
                confidence += static_weight * 0.8
            if candidate in dynamic_methods:
                confidence += dynamic_weight * 0.95

            if confidence > 0.3:
                node = self._create_fusion_node(
                    candidate, confidence, static_methods, dynamic_methods
                )
                fused.add_node(node)
                edge = ImpactEdge(source=method, target=candidate)
                fused.add_edge(edge)

        return fused

    # ==================== 并集融合策略 ====================

    def _union_fusion_upstream(
        self,
        method: str,
        static_graph: CallChainGraph | None,
        dynamic_graph: CallChainGraph | None,
        max_depth: int,
    ) -> ImpactGraph:
        """并集融合上游调用链.

        合并所有分析器的结果，去重后返回并集。

        Args:
            method: 起始方法
            static_graph: 静态分析调用链图
            dynamic_graph: 动态分析调用链图
            max_depth: 最大深度

        Returns:
            ImpactGraph: 融合后的影响图
        """
        fused = ImpactGraph(change_set_id=f"fusion_union_{method}")

        root_node = self._create_root_node(method)
        fused.add_node(root_node)
        fused.root_methods.append(method)

        static_methods = static_graph.get_all_methods() if static_graph else []
        dynamic_methods = dynamic_graph.get_all_methods() if dynamic_graph else []

        # 并集：所有方法都包含
        all_methods = set(static_methods + dynamic_methods)

        for candidate in all_methods:
            # 计算置信度（简单平均）
            confidence = 0.5
            if candidate in static_methods:
                confidence = 0.8
            if candidate in dynamic_methods:
                confidence = max(confidence, 0.95)

            node = self._create_fusion_node(candidate, confidence, static_methods, dynamic_methods)
            fused.add_node(node)
            edge = ImpactEdge(source=candidate, target=method)
            fused.add_edge(edge)

        return fused

    def _union_fusion_downstream(
        self,
        method: str,
        static_graph: CallChainGraph | None,
        dynamic_graph: CallChainGraph | None,
        max_depth: int,
    ) -> ImpactGraph:
        """并集融合下游调用链."""
        fused = ImpactGraph(change_set_id=f"fusion_union_{method}")

        root_node = self._create_root_node(method)
        fused.add_node(root_node)
        fused.root_methods.append(method)

        static_methods = static_graph.get_all_methods() if static_graph else []
        dynamic_methods = dynamic_graph.get_all_methods() if dynamic_graph else []

        all_methods = set(static_methods + dynamic_methods)

        for candidate in all_methods:
            confidence = 0.5
            if candidate in static_methods:
                confidence = 0.8
            if candidate in dynamic_methods:
                confidence = max(confidence, 0.95)

            node = self._create_fusion_node(candidate, confidence, static_methods, dynamic_methods)
            fused.add_node(node)
            edge = ImpactEdge(source=method, target=candidate)
            fused.add_edge(edge)

        return fused

    # ==================== 交集融合策略 ====================

    def _intersection_fusion_upstream(
        self,
        method: str,
        static_graph: CallChainGraph | None,
        dynamic_graph: CallChainGraph | None,
        max_depth: int,
    ) -> ImpactGraph:
        """交集融合上游调用链.

        只保留被所有分析器都识别的方法（交集）。
        如果只有一个分析器可用，则返回该分析器的结果。

        Args:
            method: 起始方法
            static_graph: 静态分析调用链图
            dynamic_graph: 动态分析调用链图
            max_depth: 最大深度

        Returns:
            ImpactGraph: 融合后的影响图
        """
        fused = ImpactGraph(change_set_id=f"fusion_intersection_{method}")

        root_node = self._create_root_node(method)
        fused.add_node(root_node)
        fused.root_methods.append(method)

        static_methods = static_graph.get_all_methods() if static_graph else []
        dynamic_methods = dynamic_graph.get_all_methods() if dynamic_graph else []

        # 确定交集
        analyzer_count = sum([1 for a in [static_graph, dynamic_graph] if a is not None])

        if analyzer_count <= 1:
            # 只有一个分析器，返回全部结果
            common_methods = set(static_methods + dynamic_methods)
        else:
            # 多个分析器，取交集
            common_methods = set(static_methods)
            if dynamic_graph:
                common_methods &= set(dynamic_methods)

        for candidate in common_methods:
            # 交集方法置信度最高
            confidence = 0.95

            node = self._create_fusion_node(candidate, confidence, static_methods, dynamic_methods)
            fused.add_node(node)
            edge = ImpactEdge(source=candidate, target=method)
            fused.add_edge(edge)

        return fused

    def _intersection_fusion_downstream(
        self,
        method: str,
        static_graph: CallChainGraph | None,
        dynamic_graph: CallChainGraph | None,
        max_depth: int,
    ) -> ImpactGraph:
        """交集融合下游调用链."""
        fused = ImpactGraph(change_set_id=f"fusion_intersection_{method}")

        root_node = self._create_root_node(method)
        fused.add_node(root_node)
        fused.root_methods.append(method)

        static_methods = static_graph.get_all_methods() if static_graph else []
        dynamic_methods = dynamic_graph.get_all_methods() if dynamic_graph else []

        analyzer_count = sum([1 for a in [static_graph, dynamic_graph] if a is not None])

        if analyzer_count <= 1:
            common_methods = set(static_methods + dynamic_methods)
        else:
            common_methods = set(static_methods)
            if dynamic_graph:
                common_methods &= set(dynamic_methods)

        for candidate in common_methods:
            confidence = 0.95

            node = self._create_fusion_node(candidate, confidence, static_methods, dynamic_methods)
            fused.add_node(node)
            edge = ImpactEdge(source=method, target=candidate)
            fused.add_edge(edge)

        return fused
