"""严重程度评定增强器单元测试."""

import pytest

from jcia.core.entities.impact_graph import ImpactSeverity
from jcia.core.services.severity_calculator import (
    MultiDimensionalSeverityCalculator,
    SeverityCalculationResult,
    SeverityDimension,
)
from jcia.core.services.severity_enhancer import SeverityEnhancer


class TestSeverityEnhancerInitialization:
    """严重程度增强器初始化测试."""

    def test_default_initialization(self) -> None:
        """测试默认初始化."""
        enhancer = SeverityEnhancer()
        assert enhancer.is_multi_dimensional_enabled is True
        assert isinstance(enhancer._calculator, MultiDimensionalSeverityCalculator)

    def test_initialization_with_custom_calculator(self) -> None:
        """测试使用自定义计算器初始化."""
        calculator = MultiDimensionalSeverityCalculator()
        enhancer = SeverityEnhancer(calculator=calculator)
        assert enhancer._calculator is calculator

    def test_initialization_with_disabled_multi_dimensional(self) -> None:
        """测试禁用多维度评分初始化."""
        enhancer = SeverityEnhancer(enable_multi_dimensional=False)
        assert enhancer.is_multi_dimensional_enabled is False


class TestSeverityEnhancerDetermineSeverity:
    """严重程度判定测试."""

    @pytest.fixture
    def enhancer(self) -> SeverityEnhancer:
        """创建增强器实例."""
        return SeverityEnhancer()

    def test_determine_severity_with_multi_dimensional(self, enhancer: SeverityEnhancer) -> None:
        """测试启用多维度评分时的严重程度判定."""
        severity = enhancer.determine_severity(
            class_name="OrderCoreService",
            method_name="processTransaction",
            method_metadata={"cyclomatic_complexity": 20, "lines_of_code": 100},
            call_depth=5,
            test_coverage=0.2,
            change_frequency=8,
        )
        assert isinstance(severity, ImpactSeverity)
        # 高复杂度、高深度、低覆盖率、频繁变更，应该是高风险
        assert severity == ImpactSeverity.HIGH

    def test_determine_severity_with_simple_class(self, enhancer: SeverityEnhancer) -> None:
        """测试简单类的严重程度判定."""
        severity = enhancer.determine_severity(
            class_name="ConfigUtil",
            method_name="getProperty",
            method_metadata={"cyclomatic_complexity": 2, "lines_of_code": 10},
            call_depth=1,
            test_coverage=0.9,
            change_frequency=1,
        )
        # 低复杂度、高覆盖率、低变更频率，应该是低风险
        assert severity in [ImpactSeverity.LOW, ImpactSeverity.MEDIUM]

    def test_determine_severity_disabled_multi_dimensional(self, enhancer: SeverityEnhancer) -> None:
        """测试禁用多维度评分时的回退."""
        enhancer.set_multi_dimensional_enabled(False)

        # 应该使用简单的基于类名的判定
        high_severity = enhancer.determine_severity(class_name="OrderManager")
        assert high_severity == ImpactSeverity.HIGH

        low_severity = enhancer.determine_severity(class_name="ConfigUtil")
        assert low_severity == ImpactSeverity.LOW

        medium_severity = enhancer.determine_severity(class_name="SomeRandomClass")
        assert medium_severity == ImpactSeverity.MEDIUM

    def test_determine_severity_with_default_params(self, enhancer: SeverityEnhancer) -> None:
        """测试使用默认参数的判定."""
        severity = enhancer.determine_severity(class_name="TestService")
        assert isinstance(severity, ImpactSeverity)


class TestSeverityEnhancerDetailedCalculation:
    """详细计算测试."""

    @pytest.fixture
    def enhancer(self) -> SeverityEnhancer:
        """创建增强器实例."""
        return SeverityEnhancer()

    def test_calculate_detailed(self, enhancer: SeverityEnhancer) -> None:
        """测试详细计算."""
        result = enhancer.calculate_detailed(
            class_name="OrderCoreService",
            method_name="processTransaction",
            method_metadata={"cyclomatic_complexity": 15, "lines_of_code": 80},
            call_depth=3,
            test_coverage=0.4,
            change_frequency=5,
        )

        assert isinstance(result, SeverityCalculationResult)
        assert 0.0 <= result.final_score <= 100.0
        assert isinstance(result.severity, ImpactSeverity)
        assert len(result.dimension_scores) == 6

        # 验证元数据
        assert result.metadata["class_name"] == "OrderCoreService"
        assert result.metadata["method_name"] == "processTransaction"

    def test_calculate_detailed_with_minimal_params(self, enhancer: SeverityEnhancer) -> None:
        """测试使用最少参数的详细计算."""
        result = enhancer.calculate_detailed(class_name="TestService")

        assert isinstance(result, SeverityCalculationResult)
        assert len(result.dimension_scores) == 6


class TestSeverityEnhancerWeightManagement:
    """权重管理测试."""

    @pytest.fixture
    def enhancer(self) -> SeverityEnhancer:
        """创建增强器实例."""
        return SeverityEnhancer()

    def test_update_weights(self, enhancer: SeverityEnhancer) -> None:
        """测试更新权重."""
        new_weights = {
            SeverityDimension.CLASS_KEYWORDS: 0.5,
            SeverityDimension.METHOD_COMPLEXITY: 0.3,
            SeverityDimension.CALL_DEPTH: 0.2,
            SeverityDimension.TEST_COVERAGE: 0.0,
            SeverityDimension.CHANGE_FREQUENCY: 0.0,
            SeverityDimension.BUSINESS_CRITICALITY: 0.0,
        }

        enhancer.update_weights(new_weights)
        weights = enhancer.get_weights()

        assert weights[SeverityDimension.CLASS_KEYWORDS] == 0.5
        assert weights[SeverityDimension.METHOD_COMPLEXITY] == 0.3
        assert weights[SeverityDimension.CALL_DEPTH] == 0.2

    def test_get_weights(self, enhancer: SeverityEnhancer) -> None:
        """测试获取权重."""
        weights = enhancer.get_weights()

        assert isinstance(weights, dict)
        assert len(weights) == 6
        assert all(isinstance(w, float) for w in weights.values())
        assert abs(sum(weights.values()) - 1.0) < 0.001


class TestSeverityEnhancerSimpleSeverity:
    """简单严重程度判定测试（回退方案）."""

    def test_high_severity_keywords(self) -> None:
        """测试高严重程度关键词."""
        enhancer = SeverityEnhancer(enable_multi_dimensional=False)

        high_classes = [
            "OrderCoreService",
            "UserManager",
            "PaymentHandler",
            "BusinessService",
            "DomainEntity",
            "UserRepository",
            "OrderDAO",
            "PaymentAdapter",
        ]

        for class_name in high_classes:
            severity = enhancer.determine_severity(class_name=class_name)
            assert severity == ImpactSeverity.HIGH, f"{class_name} should be HIGH"

    def test_low_severity_keywords(self) -> None:
        """测试低严重程度关键词."""
        enhancer = SeverityEnhancer(enable_multi_dimensional=False)

        low_classes = [
            "AppConfig",
            "SystemConstants",
            "StatusEnum",
            "UserDTO",
            "OrderVO",
            "DataModel",
            "ValidationException",  # Note: not BusinessException
            "ErrorCode",
            "StringUtil",
        ]

        for class_name in low_classes:
            severity = enhancer.determine_severity(class_name=class_name)
            assert severity == ImpactSeverity.LOW, f"{class_name} should be LOW"

    def test_medium_severity_default(self) -> None:
        """测试默认中等严重程度."""
        enhancer = SeverityEnhancer(enable_multi_dimensional=False)

        medium_classes = [
            "SomeRandomClass",
            "DataProcessor",
            "CustomComponent",
            "MyHelper",
        ]

        for class_name in medium_classes:
            severity = enhancer.determine_severity(class_name=class_name)
            assert severity == ImpactSeverity.MEDIUM, f"{class_name} should be MEDIUM"


class TestSeverityEnhancerStateManagement:
    """状态管理测试."""

    def test_multi_dimensional_enabled_property(self) -> None:
        """测试多维度启用属性."""
        enhancer = SeverityEnhancer()
        assert enhancer.is_multi_dimensional_enabled is True

        enhancer.set_multi_dimensional_enabled(False)
        assert enhancer.is_multi_dimensional_enabled is False

        enhancer.set_multi_dimensional_enabled(True)
        assert enhancer.is_multi_dimensional_enabled is True

    def test_set_multi_dimensional_enabled(self) -> None:
        """测试设置多维度启用状态."""
        enhancer = SeverityEnhancer()

        # 禁用后应使用简单判定
        enhancer.set_multi_dimensional_enabled(False)
        severity = enhancer.determine_severity(class_name="OrderManager")
        assert severity == ImpactSeverity.HIGH

        # 启用后应使用多维度判定
        enhancer.set_multi_dimensional_enabled(True)
        severity = enhancer.determine_severity(class_name="OrderManager")
        assert isinstance(severity, ImpactSeverity)
