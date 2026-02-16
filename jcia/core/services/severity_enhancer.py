"""严重程度评定增强器.

提供向后兼容的方式增强现有的严重程度评定逻辑。
"""

from typing import Any

from jcia.core.entities.impact_graph import ImpactSeverity
from jcia.core.services.severity_calculator import (
    MultiDimensionalSeverityCalculator,
    SeverityCalculationResult,
    SeverityDimension,
)


class SeverityEnhancer:
    """严重程度评定增强器.

    将多维度评分系统集成到现有的CallChainBuilder中，
    提供向后兼容的接口。
    """

    def __init__(
        self,
        calculator: MultiDimensionalSeverityCalculator | None = None,
        enable_multi_dimensional: bool = True,
    ) -> None:
        """初始化增强器.

        Args:
            calculator: 多维度计算器实例，为None则创建默认实例
            enable_multi_dimensional: 是否启用多维度评分
        """
        self._calculator = calculator or MultiDimensionalSeverityCalculator()
        self._enable_multi_dimensional = enable_multi_dimensional

    def determine_severity(
        self,
        class_name: str,
        method_name: str = "",
        method_metadata: dict[str, Any] | None = None,
        call_depth: int = 0,
        test_coverage: float = 0.0,
        change_frequency: int = 0,
    ) -> ImpactSeverity:
        """确定影响严重程度.

        如果启用了多维度评分，则使用多维度计算器；
        否则回退到基于类名的简单评分。

        Args:
            class_name: 类名
            method_name: 方法名
            method_metadata: 方法元数据
            call_depth: 调用链深度
            test_coverage: 测试覆盖率
            change_frequency: 变更频率

        Returns:
            ImpactSeverity: 影响严重程度
        """
        if not self._enable_multi_dimensional:
            return self._determine_severity_simple(class_name)

        result = self._calculator.calculate(
            class_name=class_name,
            method_name=method_name,
            method_metadata=method_metadata,
            call_depth=call_depth,
            test_coverage=test_coverage,
            change_frequency=change_frequency,
        )
        return result.severity

    def calculate_detailed(
        self,
        class_name: str,
        method_name: str = "",
        method_metadata: dict[str, Any] | None = None,
        call_depth: int = 0,
        test_coverage: float = 0.0,
        change_frequency: int = 0,
    ) -> SeverityCalculationResult:
        """计算详细的严重程度.

        返回包含各维度评分的详细结果。

        Args:
            class_name: 类名
            method_name: 方法名
            method_metadata: 方法元数据
            call_depth: 调用链深度
            test_coverage: 测试覆盖率
            change_frequency: 变更频率

        Returns:
            SeverityCalculationResult: 详细计算结果
        """
        return self._calculator.calculate(
            class_name=class_name,
            method_name=method_name,
            method_metadata=method_metadata,
            call_depth=call_depth,
            test_coverage=test_coverage,
            change_frequency=change_frequency,
        )

    def _determine_severity_simple(self, class_name: str) -> ImpactSeverity:
        """简单的严重程度判定（回退方案）.

        Args:
            class_name: 类名

        Returns:
            ImpactSeverity: 严重程度
        """
        class_name_lower = class_name.lower()

        # 高严重程度关键词
        high_keywords = [
            "core", "kernel", "manager", "handler", "service",
            "controller", "business", "domain", "entity",
            "repository", "dao", "mapper", "adapter",
        ]
        if any(keyword in class_name_lower for keyword in high_keywords):
            return ImpactSeverity.HIGH

        # 低严重程度关键词
        low_keywords = [
            "config", "constant", "enum", "dto", "vo",
            "pojo", "model", "exception", "error", "util",
        ]
        if any(keyword in class_name_lower for keyword in low_keywords):
            return ImpactSeverity.LOW

        return ImpactSeverity.MEDIUM

    def update_weights(self, weights: dict[SeverityDimension, float]) -> None:
        """更新权重配置.

        Args:
            weights: 新的权重配置
        """
        self._calculator.update_weights(weights)

    def get_weights(self) -> dict[SeverityDimension, float]:
        """获取当前权重配置.

        Returns:
            Dict[SeverityDimension, float]: 权重配置
        """
        return self._calculator.get_weights()

    @property
    def is_multi_dimensional_enabled(self) -> bool:
        """是否启用了多维度评分."""
        return self._enable_multi_dimensional

    def set_multi_dimensional_enabled(self, enabled: bool) -> None:
        """设置是否启用多维度评分.

        Args:
            enabled: 是否启用
        """
        self._enable_multi_dimensional = enabled
