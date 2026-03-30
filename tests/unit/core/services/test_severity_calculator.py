"""多维度严重程度计算器单元测试."""

import pytest

from jcia.core.entities.impact_graph import ImpactSeverity
from jcia.core.services.severity_calculator import (
    DimensionScore,
    MultiDimensionalSeverityCalculator,
    SeverityCalculationResult,
    SeverityDimension,
)


class TestSeverityDimension:
    """严重程度维度枚举测试."""

    def test_dimension_values(self) -> None:
        """测试维度枚举值."""
        assert SeverityDimension.CLASS_KEYWORDS.value == "class_keywords"
        assert SeverityDimension.METHOD_COMPLEXITY.value == "method_complexity"
        assert SeverityDimension.CALL_DEPTH.value == "call_depth"
        assert SeverityDimension.TEST_COVERAGE.value == "test_coverage"
        assert SeverityDimension.CHANGE_FREQUENCY.value == "change_frequency"
        assert SeverityDimension.BUSINESS_CRITICALITY.value == "business_criticality"


class TestDimensionScore:
    """维度评分数据类测试."""

    def test_dimension_score_creation(self) -> None:
        """测试创建维度评分."""
        score = DimensionScore(
            dimension=SeverityDimension.CLASS_KEYWORDS,
            score=80.0,
            weight=0.25,
            details={"class_name": "OrderService"},
        )
        assert score.dimension == SeverityDimension.CLASS_KEYWORDS
        assert score.score == 80.0
        assert score.weight == 0.25
        assert score.details["class_name"] == "OrderService"

    def test_weighted_score_calculation(self) -> None:
        """测试加权分数计算."""
        score = DimensionScore(
            dimension=SeverityDimension.METHOD_COMPLEXITY,
            score=90.0,
            weight=0.2,
        )
        assert score.weighted_score == 18.0  # 90 * 0.2


class TestMultiDimensionalSeverityCalculator:
    """多维度严重程度计算器测试."""

    @pytest.fixture
    def calculator(self) -> MultiDimensionalSeverityCalculator:
        """创建计算器实例."""
        return MultiDimensionalSeverityCalculator()

    def test_initialization(self) -> None:
        """测试计算器初始化."""
        calculator = MultiDimensionalSeverityCalculator()
        weights = calculator.get_weights()

        # 验证默认权重
        assert SeverityDimension.CLASS_KEYWORDS in weights
        assert SeverityDimension.METHOD_COMPLEXITY in weights
        assert SeverityDimension.CALL_DEPTH in weights
        assert SeverityDimension.TEST_COVERAGE in weights
        assert SeverityDimension.CHANGE_FREQUENCY in weights
        assert SeverityDimension.BUSINESS_CRITICALITY in weights

        # 验证权重总和为1
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.001

    def test_weight_normalization(self) -> None:
        """测试权重归一化."""
        custom_weights = {
            SeverityDimension.CLASS_KEYWORDS: 1.0,
            SeverityDimension.METHOD_COMPLEXITY: 1.0,
            SeverityDimension.CALL_DEPTH: 1.0,
            SeverityDimension.TEST_COVERAGE: 1.0,
            SeverityDimension.CHANGE_FREQUENCY: 1.0,
            SeverityDimension.BUSINESS_CRITICALITY: 1.0,
        }
        calculator = MultiDimensionalSeverityCalculator(weights=custom_weights)
        weights = calculator.get_weights()

        # 验证权重已归一化（每个应为1/6）
        for weight in weights.values():
            assert abs(weight - 1.0 / 6.0) < 0.001

    def test_class_keyword_score_calculation(self, calculator: MultiDimensionalSeverityCalculator) -> None:
        """测试类名关键词评分."""
        # 测试核心类（高分数）
        assert calculator._calculate_class_keyword_score("OrderCoreService") == 100.0
        assert calculator._calculate_class_keyword_score("UserManager") == 90.0
        assert calculator._calculate_class_keyword_score("PaymentHandler") == 90.0

        # 测试中等分数
        assert calculator._calculate_class_keyword_score("OrderProcessor") == 65.0
        assert calculator._calculate_class_keyword_score("ReportBuilder") == 60.0

        # 测试低分数
        assert calculator._calculate_class_keyword_score("AppConfig") == 30.0
        assert calculator._calculate_class_keyword_score("Constants") == 20.0

        # 测试未知类名（默认中等）
        default_score = calculator._calculate_class_keyword_score("SomeRandomClass")
        assert default_score == 50.0

    def test_complexity_score_calculation(self, calculator: MultiDimensionalSeverityCalculator) -> None:
        """测试复杂度评分."""
        # 高复杂度
        high_complexity = {"cyclomatic_complexity": 25, "lines_of_code": 150}
        high_score = calculator._calculate_complexity_score(high_complexity)
        assert high_score >= 90.0

        # 中等复杂度
        medium_complexity = {"cyclomatic_complexity": 15, "lines_of_code": 60}
        medium_score = calculator._calculate_complexity_score(medium_complexity)
        assert 50.0 <= medium_score <= 90.0

        # 低复杂度
        low_complexity = {"cyclomatic_complexity": 5, "lines_of_code": 20}
        low_score = calculator._calculate_complexity_score(low_complexity)
        assert low_score < 70.0

        # 空元数据
        empty_score = calculator._calculate_complexity_score({})
        assert 0.0 <= empty_score <= 50.0

    def test_depth_score_calculation(self, calculator: MultiDimensionalSeverityCalculator) -> None:
        """测试调用链深度评分."""
        # 深层调用
        assert calculator._calculate_depth_score(5) == 100.0
        assert calculator._calculate_depth_score(7) == 100.0

        # 中等深度
        moderate_score = calculator._calculate_depth_score(3)
        assert 70.0 <= moderate_score <= 100.0

        moderate_score2 = calculator._calculate_depth_score(4)
        assert moderate_score2 > moderate_score  # 深度越大分数越高

        # 浅层调用
        shallow_score = calculator._calculate_depth_score(1)
        assert 30.0 <= shallow_score <= 50.0

        # 零深度
        zero_score = calculator._calculate_depth_score(0)
        assert 0.0 <= zero_score <= 40.0

    def test_coverage_score_calculation(self, calculator: MultiDimensionalSeverityCalculator) -> None:
        """测试测试覆盖率评分（覆盖率越低，分数越高）."""
        # 未覆盖（最高风险）
        assert calculator._calculate_coverage_score(0.0) == 100.0

        # 低覆盖率
        low_coverage = calculator._calculate_coverage_score(0.2)
        assert low_coverage >= 80.0

        # 中等覆盖率
        medium_coverage = calculator._calculate_coverage_score(0.5)
        assert 40.0 <= medium_coverage <= 80.0

        # 较高覆盖率
        high_coverage = calculator._calculate_coverage_score(0.75)
        assert 0.0 <= high_coverage <= 60.0

        # 完全覆盖（最低风险）
        full_coverage = calculator._calculate_coverage_score(1.0)
        assert 0.0 <= full_coverage <= 20.0

    def test_frequency_score_calculation(self, calculator: MultiDimensionalSeverityCalculator) -> None:
        """测试变更频率评分（变更越频繁，分数越高）."""
        # 频繁变更
        assert calculator._calculate_frequency_score(10) == 100.0
        assert calculator._calculate_frequency_score(15) == 100.0

        # 较频繁变更
        frequent = calculator._calculate_frequency_score(7)
        assert 80.0 <= frequent <= 100.0

        # 中等频率
        medium = calculator._calculate_frequency_score(3)
        assert 40.0 <= medium <= 70.0

        # 较低频率
        low = calculator._calculate_frequency_score(1)
        assert 0.0 <= low <= 30.0

        # 无变更
        zero = calculator._calculate_frequency_score(0)
        assert zero == 0.0

    def test_business_criticality_score(self, calculator: MultiDimensionalSeverityCalculator) -> None:
        """测试业务关键性评分."""
        # 高业务关键性（支付、交易、用户相关）
        assert calculator._calculate_business_criticality(
            "PaymentService", "processPayment"
        ) == 100.0
        assert calculator._calculate_business_criticality(
            "OrderManager", "createOrder"
        ) == 100.0
        assert calculator._calculate_business_criticality(
            "UserAuth", "login"
        ) == 100.0

        # 中等业务关键性（查询类）
        medium = calculator._calculate_business_criticality(
            "ProductQuery", "findProducts"
        )
        assert 40.0 <= medium <= 70.0

        # 低业务关键性（工具类）
        low = calculator._calculate_business_criticality(
            "StringUtil", "trim"
        )
        assert low <= 50.0

    def test_calculate_integration(self, calculator: MultiDimensionalSeverityCalculator) -> None:
        """测试综合计算."""
        result = calculator.calculate(
            class_name="PaymentCoreService",
            method_name="processTransaction",
            method_metadata={"cyclomatic_complexity": 15, "lines_of_code": 80},
            call_depth=3,
            test_coverage=0.3,
            change_frequency=5,
        )

        assert isinstance(result, SeverityCalculationResult)
        assert 0.0 <= result.final_score <= 100.0
        assert isinstance(result.severity, ImpactSeverity)
        assert len(result.dimension_scores) == 6  # 6个维度

        # 验证各维度都有评分
        dimensions = [ds.dimension for ds in result.dimension_scores]
        assert SeverityDimension.CLASS_KEYWORDS in dimensions
        assert SeverityDimension.METHOD_COMPLEXITY in dimensions
        assert SeverityDimension.CALL_DEPTH in dimensions
        assert SeverityDimension.TEST_COVERAGE in dimensions
        assert SeverityDimension.CHANGE_FREQUENCY in dimensions
        assert SeverityDimension.BUSINESS_CRITICALITY in dimensions

    def test_score_to_severity_conversion(self, calculator: MultiDimensionalSeverityCalculator) -> None:
        """测试分数到严重程度的转换."""
        # 高风险分数
        assert calculator._score_to_severity(90.0) == ImpactSeverity.HIGH
        assert calculator._score_to_severity(70.0) == ImpactSeverity.HIGH

        # 中等风险分数
        assert calculator._score_to_severity(69.0) == ImpactSeverity.MEDIUM
        assert calculator._score_to_severity(50.0) == ImpactSeverity.MEDIUM
        assert calculator._score_to_severity(40.0) == ImpactSeverity.MEDIUM

        # 低风险分数
        assert calculator._score_to_severity(39.0) == ImpactSeverity.LOW
        assert calculator._score_to_severity(10.0) == ImpactSeverity.LOW
        assert calculator._score_to_severity(0.0) == ImpactSeverity.LOW

    def test_custom_weights(self) -> None:
        """测试自定义权重."""
        custom_weights = {
            SeverityDimension.CLASS_KEYWORDS: 0.5,
            SeverityDimension.METHOD_COMPLEXITY: 0.3,
            SeverityDimension.CALL_DEPTH: 0.2,
            SeverityDimension.TEST_COVERAGE: 0.0,
            SeverityDimension.CHANGE_FREQUENCY: 0.0,
            SeverityDimension.BUSINESS_CRITICALITY: 0.0,
        }
        calculator = MultiDimensionalSeverityCalculator(weights=custom_weights)
        result = calculator.calculate(
            class_name="TestService",
            method_name="testMethod",
        )

        # 验证权重已应用
        assert result is not None  # noqa: F841
        weights = calculator.get_weights()
        assert weights[SeverityDimension.CLASS_KEYWORDS] == 0.5
        assert weights[SeverityDimension.METHOD_COMPLEXITY] == 0.3
        assert weights[SeverityDimension.CALL_DEPTH] == 0.2


class TestSeverityCalculationResult:
    """严重程度计算结果测试."""

    def test_result_creation(self) -> None:
        """测试创建计算结果."""
        dimension_scores = [
            DimensionScore(
                dimension=SeverityDimension.CLASS_KEYWORDS,
                score=80.0,
                weight=0.25,
            ),
            DimensionScore(
                dimension=SeverityDimension.METHOD_COMPLEXITY,
                score=60.0,
                weight=0.2,
            ),
        ]
        result = SeverityCalculationResult(
            final_score=70.0,
            severity=ImpactSeverity.HIGH,
            dimension_scores=dimension_scores,
            metadata={"test": "data"},
        )

        assert result.final_score == 70.0
        assert result.severity == ImpactSeverity.HIGH
        assert len(result.dimension_scores) == 2
        assert result.metadata["test"] == "data"

    def test_get_dimension_score(self) -> None:
        """测试获取指定维度评分."""
        dimension_scores = [
            DimensionScore(
                dimension=SeverityDimension.CLASS_KEYWORDS,
                score=80.0,
                weight=0.25,
            ),
            DimensionScore(
                dimension=SeverityDimension.METHOD_COMPLEXITY,
                score=60.0,
                weight=0.2,
            ),
        ]
        result = SeverityCalculationResult(
            final_score=70.0,
            severity=ImpactSeverity.HIGH,
            dimension_scores=dimension_scores,
        )

        # 获取存在的维度
        class_score = result.get_dimension_score(SeverityDimension.CLASS_KEYWORDS)
        assert class_score is not None
        assert class_score.score == 80.0

        # 获取不存在的维度
        non_existent = result.get_dimension_score(SeverityDimension.CALL_DEPTH)
        assert non_existent is None
