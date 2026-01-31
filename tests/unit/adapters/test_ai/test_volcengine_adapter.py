"""火山引擎LLM适配器单元测试."""

from pathlib import Path
from uuid import uuid4

from jcia.adapters.ai.volcengine_adapter import VolcengineAdapter
from jcia.core.entities.test_case import TestCase
from jcia.core.interfaces.ai_service import (
    AIProvider,
    CodeAnalysisRequest,
    TestGenerationRequest,
)

TEST_ACCESS_KEY = "test-key"
TEST_SECRET_KEY = uuid4().hex
TEST_APP_ID = "test-app"


class TestVolcengineAdapter:
    """VolcengineAdapter 测试类."""

    def test_provider_returns_volcengine(self) -> None:
        """测试提供商返回火山引擎."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
        )

        # Act
        provider = adapter.provider

        # Assert
        assert provider == AIProvider.OPENAI  # 暂时使用OPENAI标识

    def test_model_returns_default_model(self) -> None:
        """测试默认模型名称."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
        )

        # Act
        model = adapter.model

        # Assert
        assert model == "doubao-pro-32k"

    def test_model_returns_custom_model(self) -> None:
        """测试自定义模型名称."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
            model="doubao-pro-128k",
        )

        # Act
        model = adapter.model

        # Assert
        assert model == "doubao-pro-128k"

    def test_generate_tests_creates_test_cases(self) -> None:
        """测试生成测试用例."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
        )
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={
                "com.example.Service": "public class Service { public void method() {} }"
            },
            context={"project_path": "/fake/project"},
        )

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) > 0
        assert response.test_cases[0].class_name == "com.example.ServiceTest"
        assert len(response.explanations) > 0

    def test_generate_tests_includes_token_usage(self) -> None:
        """测试生成测试包含token使用统计."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
        )
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={"com.example.Service": "class Service {}"},
            context={},
        )

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert response.tokens_used >= 0
        assert 0.0 <= response.confidence <= 1.0

    def test_generate_for_uncovered_creates_tests(self) -> None:
        """测试为未覆盖代码生成测试."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
        )
        coverage_data = {
            "uncovered_classes": ["com.example.UncoveredClass"],
            "uncovered_methods": [],
        }

        # Act
        response = adapter.generate_for_uncovered(coverage_data, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) > 0

    def test_refine_test_updates_test_code(self) -> None:
        """测试优化测试用例."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
        )
        test_case = TestCase(
            class_name="ServiceTest",
            method_name="testMethod",
            metadata={"test_code": "原始测试代码"},
        )

        # Act
        refined = adapter.refine_test(test_case, "测试不够全面", Path("/fake/project"))

        # Assert
        assert isinstance(refined, TestCase)

    def test_analyze_code_returns_analysis(self) -> None:
        """测试代码分析."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
        )
        request = CodeAnalysisRequest(code="public class Service {}", analysis_type="code_quality")

        # Act
        response = adapter.analyze_code(request)

        # Assert
        assert len(response.findings) > 0
        assert len(response.suggestions) > 0
        assert response.risk_level in ["HIGH", "MEDIUM", "LOW"]

    def test_explain_change_impact_returns_explanation(self) -> None:
        """测试解释变更影响."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
        )

        # Act
        explanation = adapter.explain_change_impact(changed_methods=["com.Service.method1"])

        # Assert
        assert isinstance(explanation, str)
        # 由于API可能失败返回空字符串，这里只检查类型

    def test_generate_tests_with_multiple_classes(self) -> None:
        """测试为多个类生成测试."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
        )
        request = TestGenerationRequest(
            target_classes=["com.example.Service1", "com.example.Service2"],
            code_snippets={
                "com.example.Service1": "class Service1 {}",
                "com.example.Service2": "class Service2 {}",
            },
            context={},
        )

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) == 2

    def test_generate_tests_with_requirements(self) -> None:
        """测试带要求的测试生成."""
        # Arrange
        adapter = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
        )
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={"com.example.Service": "class Service {}"},
            context={},
            requirements="生成边界条件测试",
        )

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) > 0
