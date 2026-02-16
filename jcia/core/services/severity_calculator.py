"""多维度严重程度评定服务.

实现基于多维度评分的综合严重程度计算。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from jcia.core.entities.impact_graph import ImpactSeverity


class SeverityDimension(Enum):
    """严重程度评定维度枚举."""

    CLASS_KEYWORDS = "class_keywords"  # 类名关键词
    METHOD_COMPLEXITY = "method_complexity"  # 方法复杂度
    CALL_DEPTH = "call_depth"  # 调用链深度
    TEST_COVERAGE = "test_coverage"  # 测试覆盖率
    CHANGE_FREQUENCY = "change_frequency"  # 变更频率
    BUSINESS_CRITICALITY = "business_criticality"  # 业务关键性


@dataclass
class DimensionScore:
    """维度评分.

    Attributes:
        dimension: 评分维度
        score: 分数 (0-100)
        weight: 权重 (0-1)
        details: 评分详情
    """

    dimension: SeverityDimension
    score: float = 0.0
    weight: float = 1.0
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        """加权分数."""
        return self.score * self.weight


@dataclass
class SeverityCalculationResult:
    """严重程度计算结果.

    Attributes:
        final_score: 最终分数 (0-100)
        severity: 严重程度等级
        dimension_scores: 各维度评分
        metadata: 额外元数据
    """

    final_score: float
    severity: ImpactSeverity
    dimension_scores: list[DimensionScore] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_dimension_score(self, dimension: SeverityDimension) -> DimensionScore | None:
        """获取指定维度的评分.

        Args:
            dimension: 评分维度

        Returns:
            Optional[DimensionScore]: 维度评分
        """
        for score in self.dimension_scores:
            if score.dimension == dimension:
                return score
        return None


class MultiDimensionalSeverityCalculator:
    """多维度严重程度计算器.

    基于多个维度综合评定影响严重程度。
    """

    # 默认权重配置
    DEFAULT_WEIGHTS: dict[SeverityDimension, float] = {
        SeverityDimension.CLASS_KEYWORDS: 0.25,
        SeverityDimension.METHOD_COMPLEXITY: 0.20,
        SeverityDimension.CALL_DEPTH: 0.15,
        SeverityDimension.TEST_COVERAGE: 0.15,
        SeverityDimension.CHANGE_FREQUENCY: 0.10,
        SeverityDimension.BUSINESS_CRITICALITY: 0.15,
    }

    # 类名关键词评分配置
    CLASS_KEYWORD_SCORES: dict[str, int] = {
        # 高严重程度关键词 (100分)
        "core": 100,
        "kernel": 100,
        "manager": 90,
        "handler": 90,
        "service": 85,
        "controller": 85,
        "business": 85,
        "domain": 85,
        "entity": 80,
        "repository": 80,
        "dao": 80,
        "mapper": 75,
        "adapter": 75,
        # 中严重程度关键词 (50-70分)
        "component": 65,
        "processor": 65,
        "builder": 60,
        "factory": 60,
        "provider": 55,
        "helper": 50,
        "util": 50,
        # 低严重程度关键词 (0-40分)
        "config": 30,
        "configuration": 30,
        "constant": 20,
        "constants": 20,
        "enum": 20,
        "dto": 25,
        "vo": 25,
        "pojo": 25,
        "model": 30,
        "exception": 15,
        "error": 15,
    }

    # 复杂度阈值配置
    COMPLEXITY_THRESHOLDS = {
        "high": 20,  # 圈复杂度 >= 20 为高风险
        "medium": 10,  # 圈复杂度 >= 10 为中风险
    }

    # 调用链深度阈值配置
    DEPTH_THRESHOLDS = {
        "deep": 5,  # 深度 >= 5 为深层调用
        "moderate": 3,  # 深度 >= 3 为中等深度
    }

    def __init__(
        self,
        weights: dict[SeverityDimension, float] | None = None,
    ) -> None:
        """初始化计算器.

        Args:
            weights: 自定义权重配置，默认为DEFAULT_WEIGHTS
        """
        self._weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._normalize_weights()

    def _normalize_weights(self) -> None:
        """归一化权重，确保总和为1."""
        total = sum(self._weights.values())
        if total > 0 and total != 1.0:
            for key in self._weights:
                self._weights[key] /= total

    def calculate(
        self,
        class_name: str,
        method_name: str,
        method_metadata: dict[str, Any] | None = None,
        call_depth: int = 0,
        test_coverage: float = 0.0,
        change_frequency: int = 0,
    ) -> SeverityCalculationResult:
        """计算综合严重程度.

        Args:
            class_name: 类名
            method_name: 方法名
            method_metadata: 方法元数据（复杂度、行数等）
            call_depth: 调用链深度
            test_coverage: 测试覆盖率 (0-1)
            change_frequency: 变更频率（近N次提交中变更次数）

        Returns:
            SeverityCalculationResult: 计算结果
        """
        method_metadata = method_metadata or {}
        dimension_scores: list[DimensionScore] = []

        # 1. 类名关键词评分
        class_keyword_score = self._calculate_class_keyword_score(class_name)
        dimension_scores.append(
            DimensionScore(
                dimension=SeverityDimension.CLASS_KEYWORDS,
                score=class_keyword_score,
                weight=self._weights[SeverityDimension.CLASS_KEYWORDS],
                details={"class_name": class_name},
            )
        )

        # 2. 方法复杂度评分
        complexity_score = self._calculate_complexity_score(method_metadata)
        dimension_scores.append(
            DimensionScore(
                dimension=SeverityDimension.METHOD_COMPLEXITY,
                score=complexity_score,
                weight=self._weights[SeverityDimension.METHOD_COMPLEXITY],
                details={
                    "cyclomatic_complexity": method_metadata.get("cyclomatic_complexity", 0),
                    "lines_of_code": method_metadata.get("lines_of_code", 0),
                },
            )
        )

        # 3. 调用链深度评分
        depth_score = self._calculate_depth_score(call_depth)
        dimension_scores.append(
            DimensionScore(
                dimension=SeverityDimension.CALL_DEPTH,
                score=depth_score,
                weight=self._weights[SeverityDimension.CALL_DEPTH],
                details={"call_depth": call_depth},
            )
        )

        # 4. 测试覆盖率评分（覆盖率越低，严重程度越高）
        coverage_score = self._calculate_coverage_score(test_coverage)
        dimension_scores.append(
            DimensionScore(
                dimension=SeverityDimension.TEST_COVERAGE,
                score=coverage_score,
                weight=self._weights[SeverityDimension.TEST_COVERAGE],
                details={"test_coverage": test_coverage},
            )
        )

        # 5. 变更频率评分（变更越频繁，风险越高）
        frequency_score = self._calculate_frequency_score(change_frequency)
        dimension_scores.append(
            DimensionScore(
                dimension=SeverityDimension.CHANGE_FREQUENCY,
                score=frequency_score,
                weight=self._weights[SeverityDimension.CHANGE_FREQUENCY],
                details={"change_frequency": change_frequency},
            )
        )

        # 6. 业务关键性评分（基于方法名和类名推断）
        business_score = self._calculate_business_criticality(
            class_name, method_name
        )
        dimension_scores.append(
            DimensionScore(
                dimension=SeverityDimension.BUSINESS_CRITICALITY,
                score=business_score,
                weight=self._weights[SeverityDimension.BUSINESS_CRITICALITY],
                details={"class_name": class_name, "method_name": method_name},
            )
        )

        # 计算最终分数
        final_score = self._calculate_final_score(dimension_scores)
        severity = self._score_to_severity(final_score)

        return SeverityCalculationResult(
            final_score=final_score,
            severity=severity,
            dimension_scores=dimension_scores,
            metadata={
                "class_name": class_name,
                "method_name": method_name,
                "method_metadata": method_metadata,
            },
        )

    def _calculate_class_keyword_score(self, class_name: str) -> float:
        """根据类名关键词计算分数.

        Args:
            class_name: 类名

        Returns:
            float: 分数 (0-100)
        """
        class_name_lower = class_name.lower()
        max_score = 0.0

        for keyword, score in self.CLASS_KEYWORD_SCORES.items():
            if keyword in class_name_lower:
                max_score = max(max_score, float(score))

        return max_score if max_score > 0 else 50.0  # 默认中等分数

    def _calculate_complexity_score(self, metadata: dict[str, Any]) -> float:
        """根据方法复杂度计算分数.

        Args:
            metadata: 方法元数据

        Returns:
            float: 分数 (0-100)，复杂度越高分数越高
        """
        # 圈复杂度
        cyclomatic = metadata.get("cyclomatic_complexity", 0)
        # 代码行数
        loc = metadata.get("lines_of_code", 0)

        # 基于圈复杂度评分
        if cyclomatic >= self.COMPLEXITY_THRESHOLDS["high"]:
            complexity_score = 100.0
        elif cyclomatic >= self.COMPLEXITY_THRESHOLDS["medium"]:
            complexity_score = 70.0 + (cyclomatic - self.COMPLEXITY_THRESHOLDS["medium"]) * 3
        else:
            complexity_score = 30.0 + cyclomatic * 4

        # 基于代码行数评分
        if loc >= 100:
            loc_score = 100.0
        elif loc >= 50:
            loc_score = 70.0 + (loc - 50) * 0.6
        else:
            loc_score = loc * 1.4

        # 综合评分（圈复杂度权重更高）
        final_score = complexity_score * 0.7 + loc_score * 0.3
        return min(100.0, max(0.0, final_score))

    def _calculate_depth_score(self, depth: int) -> float:
        """根据调用链深度计算分数.

        Args:
            depth: 调用链深度

        Returns:
            float: 分数 (0-100)
        """
        if depth >= self.DEPTH_THRESHOLDS["deep"]:
            return 100.0
        elif depth >= self.DEPTH_THRESHOLDS["moderate"]:
            return 70.0 + (depth - self.DEPTH_THRESHOLDS["moderate"]) * 15
        else:
            return 30.0 + depth * 13.33

    def _calculate_coverage_score(self, coverage: float) -> float:
        """根据测试覆盖率计算分数.

        覆盖率越低，风险越高，分数越高。

        Args:
            coverage: 测试覆盖率 (0-1)

        Returns:
            float: 分数 (0-100)
        """
        # 未覆盖 = 最高风险
        if coverage == 0:
            return 100.0
        elif coverage < 0.3:
            return 90.0 + (0.3 - coverage) * 33.33
        elif coverage < 0.6:
            return 70.0 + (0.6 - coverage) * 66.67
        elif coverage < 0.8:
            return 40.0 + (0.8 - coverage) * 150
        else:
            return max(0, 20.0 - (coverage - 0.8) * 100)

    def _calculate_frequency_score(self, frequency: int) -> float:
        """根据变更频率计算分数.

        变更越频繁，风险越高。

        Args:
            frequency: 变更频率（近N次提交中变更次数）

        Returns:
            float: 分数 (0-100)
        """
        if frequency >= 10:
            return 100.0
        elif frequency >= 5:
            return 80.0 + (frequency - 5) * 4
        elif frequency >= 2:
            return 50.0 + (frequency - 2) * 10
        else:
            return max(0, frequency * 25)

    def _calculate_business_criticality(
        self, class_name: str, method_name: str
    ) -> float:
        """根据业务关键性计算分数.

        基于类名和方法名推断业务关键性。

        Args:
            class_name: 类名
            method_name: 方法名

        Returns:
            float: 分数 (0-100)
        """
        text = (class_name + " " + method_name).lower()
        max_score = 0.0

        # 高业务关键性关键词
        critical_keywords = [
            "payment", "pay", "transaction", "order", "user", "account",
            "auth", "login", "security", "billing", "checkout", "trade",
            "transfer", "withdraw", "deposit", "balance", "credit",
            "create", "delete", "update", "save", "process",
        ]

        # 中业务关键性关键词
        medium_keywords = [
            "query", "get", "find", "search", "list", "count",
            "validate", "check", "verify", "parse", "convert",
            "calculate", "compute", "aggregate", "summarize",
            "send", "receive", "notify", "push", "pull",
        ]

        for keyword in critical_keywords:
            if keyword in text:
                max_score = max(max_score, 100.0)
                break

        if max_score == 0:
            for keyword in medium_keywords:
                if keyword in text:
                    max_score = max(max_score, 60.0)
                    break

        return max_score if max_score > 0 else 40.0  # 默认中等分数

    def _calculate_final_score(self, dimension_scores: list[DimensionScore]) -> float:
        """计算最终分数.

        Args:
            dimension_scores: 各维度评分列表

        Returns:
            float: 最终分数 (0-100)
        """
        if not dimension_scores:
            return 50.0

        total_weighted_score = sum(ds.weighted_score for ds in dimension_scores)
        total_weight = sum(ds.weight for ds in dimension_scores)

        if total_weight == 0:
            return 50.0

        return total_weighted_score / total_weight

    def _score_to_severity(self, score: float) -> ImpactSeverity:
        """将分数转换为严重程度等级.

        Args:
            score: 分数 (0-100)

        Returns:
            ImpactSeverity: 严重程度等级
        """
        if score >= 70:
            return ImpactSeverity.HIGH
        elif score >= 40:
            return ImpactSeverity.MEDIUM
        else:
            return ImpactSeverity.LOW

    def update_weights(self, weights: dict[SeverityDimension, float]) -> None:
        """更新权重配置.

        Args:
            weights: 新的权重配置
        """
        self._weights.update(weights)
        self._normalize_weights()

    def get_weights(self) -> dict[SeverityDimension, float]:
        """获取当前权重配置.

        Returns:
            Dict[SeverityDimension, float]: 权重配置
        """
        return self._weights.copy()
