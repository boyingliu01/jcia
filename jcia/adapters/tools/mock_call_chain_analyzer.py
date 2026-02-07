"""Mock调用链分析器实现.

用于测试和开发阶段，在真实调用链分析器实现之前提供基本功能。
"""

from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainAnalyzer,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)


class MockCallChainAnalyzer(CallChainAnalyzer):
    """Mock调用链分析器.

    返回空的调用链图，用于开发和测试阶段。
    """

    def __init__(self, repo_path: str) -> None:
        """初始化分析器.

        Args:
            repo_path: 项目路径（未使用，保留用于接口兼容性）
        """
        self._repo_path = repo_path

    def analyze_upstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析上游调用者（Mock实现）.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            CallChainGraph: 空的上游调用链图
        """
        return self._create_empty_graph(method, max_depth)

    def analyze_downstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析下游被调用者（Mock实现）.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            CallChainGraph: 空的下游调用链图
        """
        return self._create_empty_graph(method, max_depth)

    def analyze_both_directions(
        self, method: str, max_depth: int = 10
    ) -> tuple[CallChainGraph, CallChainGraph]:
        """同时分析上下游（Mock实现）.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            tuple[CallChainGraph, CallChainGraph]: 空的上游图和下游图
        """
        upstream = self.analyze_upstream(method, max_depth)
        downstream = self.analyze_downstream(method, max_depth)
        return upstream, downstream

    def build_full_graph(self) -> CallChainGraph:
        """构建完整的调用链图（Mock实现）.

        Returns:
            CallChainGraph: 空的调用链图
        """
        return self._create_empty_graph("root", 10)

    def _create_empty_graph(self, method: str, max_depth: int) -> CallChainGraph:
        """创建空调用链图.

        Args:
            method: 方法名
            max_depth: 最大深度

        Returns:
            CallChainGraph: 空的调用链图
        """
        # 解析类名和方法名
        class_name = ""
        method_name = method
        if "." in method:
            parts = method.split(".")
            method_name = parts[-1]
            class_name = ".".join(parts[:-1])

        root = CallChainNode(
            class_name=class_name,
            method_name=method_name,
            signature=None,
        )

        return CallChainGraph(
            root=root,
            direction=CallChainDirection.BOTH,
            max_depth=max_depth,
            total_nodes=1,
        )

    @property
    def analyzer_type(self) -> AnalyzerType:
        """返回分析器类型.

        Returns:
            AnalyzerType: 混合分析器类型
        """
        return AnalyzerType.HYBRID

    @property
    def supports_cross_service(self) -> bool:
        """是否支持跨服务分析.

        Returns:
            bool: 支持跨服务分析
        """
        return False
