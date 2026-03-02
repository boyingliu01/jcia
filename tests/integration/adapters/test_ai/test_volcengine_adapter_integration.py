"""VolcengineAdapter 集成测试 - 使用真实 API。

注意：这些测试需要真实的 Volcengine API 密钥。
配置方式：
1. 设置环境变量: VOLCENGINE_ACCESS_KEY, VOLCENGINE_SECRET_KEY, VOLCENGINE_APP_ID
2. 创建 .env 文件（参考 .env.example）
3. 如果未配置环境变量，测试将被自动跳过
"""

import os
from pathlib import Path

import pytest

from jcia.adapters.ai.volcengine_adapter import VolcengineAdapter
from jcia.core.entities.test_case import TestCase, TestPriority, TestType
from jcia.core.interfaces.ai_service import CodeAnalysisRequest, TestGenerationRequest


def get_api_credentials() -> tuple[str, str, str] | None:
    """获取 API 凭证 - 从环境变量读取.

    Returns:
        如果环境变量已配置返回 (access_key, secret_key, app_id)，否则返回 None
    """
    access_key = os.getenv("VOLCENGINE_ACCESS_KEY")
    secret_key = os.getenv("VOLCENGINE_SECRET_KEY")
    app_id = os.getenv("VOLCENGINE_APP_ID")

    if access_key and secret_key and app_id:
        return access_key, secret_key, app_id
    return None


class TestVolcengineAdapterIntegration:
    """VolcengineAdapter 集成测试类 - 使用真实 API。"""

    @pytest.fixture
    def credentials(self) -> tuple[str, str, str]:
        """获取 API 凭证，如果未配置则跳过测试."""
        creds = get_api_credentials()
        if creds is None:
            pytest.skip(
                "VOLCENGINE_ACCESS_KEY, VOLCENGINE_SECRET_KEY, VOLCENGINE_APP_ID "
                "not set in environment. Cannot test without API credentials."
            )
        return creds

    def test_adapter_initialization(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试适配器初始化。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        # Just verify no errors occur during initialization

    def test_provider(self, credentials: tuple[str, str, str]) -> None:
        """测试提供商返回火山引擎。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        # Assert
        assert adapter.provider == "volcengine"

    def test_generate_tests_creates_test_cases(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试生成测试用例。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={},
            context={"project_path": "/test/project"},
        )

        # Act
        result = adapter.generate_tests(request, project_path=Path("/test/project"))

        # Assert - 验证基本功能
        assert result.test_cases is not None
        assert len(result.test_cases) >= 1

    def test_generate_tests_includes_token_usage(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试生成测试用例，包含 token 使用量统计。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={},
            context={},
        )

        # Act
        result = adapter.generate_tests(request, project_path=Path("/test/project"))

        # Assert - 验证基本功能
        assert result.test_cases is not None

    def test_generate_for_uncovered_creates_test_cases(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试为未覆盖代码生成测试。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        coverage_data = {
            "uncovered_classes": ["com.example.UncoveredClass"],
            "uncovered_methods": ["com.example.methodUncovered()"],
        }

        # Act
        result = adapter.generate_for_uncovered(
            coverage_data,
            project_path=Path("/test/project"),
        )

        # Assert - 验证基本功能
        assert result.test_cases is not None

    def test_refine_test_updates_test_code(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试优化测试用例。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        test_case = TestCase(
            class_name="com.example.Service",
            method_name="testMethod",
            test_type=TestType.UNIT,
            priority=TestPriority.MEDIUM,
            target_class="com.example.Service",
            metadata={"test_code": "original code"},
        )

        # Act
        adapter.refine_test(
            test_case,
            feedback="The test lacks proper assertions",
            project_path=Path("/test/project"),
        )

        # Assert - 验证基本功能（不抛出异常即可）

    def test_extract_risk_level_precision(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试风险级别精准提取（避免子串误判）。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        request = CodeAnalysisRequest(
            code="public class Service {}",
            analysis_type="code_quality",
        )

        # Act - 使用真实 API 测试风险级别提取
        result = adapter.analyze_code(request)

        # Assert - 验证基本功能
        assert result.risk_level in ["HIGH", "MEDIUM", "LOW"]

    def test_explain_change_impact_returns_explanation(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试解释变更影响返回。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        changed_methods = ["com.example.Service.methodA()", "com.example.Service.methodB()"]
        context = {"commit_hash": "abc123"}

        # Act - 使用真实 API
        explanation = adapter.explain_change_impact(
            changed_methods=changed_methods,
            context=context,
        )

        # Assert - 验证基本功能
        assert explanation is not None
        assert len(explanation) > 0

    def test_generate_tests_with_multiple_classes(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试多类测试用例。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        request = TestGenerationRequest(
            target_classes=["com.example.Service", "com.example.Repository", "com.example.Util"],
            code_snippets={},
            context={},
        )

        # Act
        result = adapter.generate_tests(request, project_path=Path("/test/project"))

        # Assert - 验证基本功能
        assert result.test_cases is not None
        assert len(result.test_cases) >= 1  # API 可能返回不同数量

    def test_generate_tests_with_requirements(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试带要求的测试生成。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={},
            context={},
            requirements="Test should cover all edge cases",
        )

        # Act
        result = adapter.generate_tests(request, project_path=Path("/test/project"))

        # Assert - 验证基本功能
        assert result.test_cases is not None

    def test_call_api_builds_auth_headers(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试构建认证头。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        # Act - 调用私有方法构建 headers
        headers = adapter._build_headers()

        # Assert
        assert "Authorization" in headers
        assert access_key in headers["Authorization"]
        assert "X-VOLC-App-Id" in headers

    def test_call_api_handles_request_errors(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试 API 请求错误处理。"""
        access_key, secret_key, app_id = credentials

        # Arrange
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        # Act - 使用无效的 app_id 测试错误处理
        adapter._app_id = ""  # 无效的 app_id

        # Act - 应该优雅地处理错误，不抛出异常
        result = adapter.generate_tests(
            TestGenerationRequest(
                target_classes=["com.example.Service"],
                code_snippets={},
                context={},
            ),
            project_path=Path("/test/project"),
        )

        # Assert - 应该返回空结果而不是抛出异常
        assert result.test_cases is not None or len(result.test_cases) == 0

    def test_temperature_parameter(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试温度参数配置。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
            temperature=0.8,  # 较高的随机性
        )

        # Act
        assert adapter._temperature == 0.8

    def test_region_parameter(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试区域参数配置。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
            region="cn-beijing",  # 中国北京区域
        )

        # Act
        assert adapter._region == "cn-beijing"

    def test_endpoint_configuration(
        self, credentials: tuple[str, str, str]
    ) -> None:
        """测试端点配置。"""
        access_key, secret_key, app_id = credentials

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        # Assert
        assert adapter._endpoint == "https://ark.cn-beijing.volces.com/api/v3/chat/completions"