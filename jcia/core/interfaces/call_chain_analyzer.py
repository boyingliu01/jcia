"""调用链分析器抽象接口.

支持静态分析和动态分析扩展。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AnalyzerType(Enum):
    """分析器类型枚举."""

    STATIC = "static"  # 静态分析
    DYNAMIC = "dynamic"  # 动态分析
    HYBRID = "hybrid"  # 混合分析


class CallChainDirection(Enum):
    """调用链方向枚举."""

    UPSTREAM = "upstream"  # 上游（调用者）
    DOWNSTREAM = "downstream"  # 下游（被调用者）
    BOTH = "both"  # 双向


@dataclass
class CallChainNode:
    """调用链节点.

    Attributes:
        class_name: 类名
        method_name: 方法名
        signature: 方法签名
        service: 所属服务（微服务场景）
        timestamp: 调用时间戳（动态分析）
        trace_id: 追踪ID（动态分析）
        children: 子节点列表
    """

    class_name: str
    method_name: str
    signature: str | None = None
    service: str | None = None
    timestamp: float | None = None
    trace_id: str | None = None
    children: list["CallChainNode"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        """返回方法全限定名."""
        if self.signature:
            return f"{self.class_name}.{self.method_name}{self.signature}"
        return f"{self.class_name}.{self.method_name}"


@dataclass
class CallChainGraph:
    """调用链图."""

    root: CallChainNode
    direction: CallChainDirection
    max_depth: int
    total_nodes: int = 0

    def get_all_methods(self) -> list[str]:
        """获取图中所有方法名."""
        methods: list[str] = []
        self._traverse(self.root, methods)
        return methods

    def _traverse(self, node: CallChainNode, methods: list[str]) -> None:
        """遍历图收集方法名."""
        methods.append(node.full_name)
        for child in node.children:
            self._traverse(child, methods)


class CallChainAnalyzer(ABC):
    """调用链分析器抽象接口.

    支持静态分析（如java-all-call-graph）和动态分析（如SkyWalking）扩展。

    Example:
        ```python
        analyzer: CallChainAnalyzer = JavaAllCallGraphAdapter()
        upstream = analyzer.analyze_upstream("com.example.Service.method()")
        downstream = analyzer.analyze_downstream("com.example.Service.method()")
        ```
    """

    @abstractmethod
    def analyze_upstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析上游调用者.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            CallChainGraph: 上游调用链图
        """
        pass

    @abstractmethod
    def analyze_downstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析下游被调用者.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            CallChainGraph: 下游调用链图
        """
        pass

    @abstractmethod
    def analyze_both_directions(
        self, method: str, max_depth: int = 10
    ) -> tuple[CallChainGraph, CallChainGraph]:
        """同时分析上下游.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            tuple[CallChainGraph, CallChainGraph]: (上游图, 下游图)
        """
        pass

    @abstractmethod
    def build_full_graph(self) -> CallChainGraph:
        """构建完整的调用链图.

        Returns:
            CallChainGraph: 完整调用链图
        """
        pass

    @property
    @abstractmethod
    def analyzer_type(self) -> AnalyzerType:
        """返回分析器类型.

        Returns:
            AnalyzerType: 分析器类型
        """
        pass

    @property
    @abstractmethod
    def supports_cross_service(self) -> bool:
        """是否支持跨服务分析（动态分析器通常支持）.

        Returns:
            bool: 是否支持
        """
        pass
