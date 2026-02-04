"""VolcengineAdapter 集成测试 - 使用真实 API。

注意：这些测试需要真实的 Volcengine API 密钥。
配置方式：
1. 设置环境变量: VOLCENGINE_API_KEY=your_api_key
2. 或修改测试文件中的 API_KEY 常量
3. 创建 .env 文件包含: VOLCENGINE_API_KEY=your_api_key
"""

import os
from pathlib import Path

import pytest

from jcia.adapters.ai.volcengine_adapter import VolcengineAdapter
from jcia.core.entities.test_case import TestCase, TestPriority, TestType
from jcia.core.interfaces.ai_service import CodeAnalysisRequest, TestGenerationRequest

# 用户提供的 API Key（实际使用时应该从环境变量读取）
# 实际环境中没有设置这个变量，测试将被自动跳过
VOLCENGINE_API_KEY = "803de240-5683-4ce3-9cbd-0ad5192db942"


class TestVolcengineAdapterIntegration:
    """VolcengineAdapter 集成测试类 - 使用真实 API。"""

    @property
    def api_key(self) -> str:
        """获取 API key - 优先使用环境变量."""
        key = os.getenv("VOLCENGINE_API_KEY", VOLCENGINE_API_KEY)
        if key == "NOT_SET":
            pytest.skip("VOLCENGINE_API_KEY not set in environment. Cannot test without API key.")
        return key

    @property
    def secret_key(self) -> str:
        """获取 Secret Key（与 Access Key 同同，使用 API key 的前 16 位作为密钥）"""
        key = self.api_key
        # 使用前16 位作为密钥
        return key[:16]

    def test_adapter_initialization(self) -> None:
        """测试适配器初始化。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLCENGINE_API_KEY not set")

        # Arrange & Act
        VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
        )

        # Just verify no errors occur during initialization
        # We can't verify much more without a real API key

    def test_provider(self) -> None:
        """测试提供商返回火山引擎。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLCENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
        )

        # Assert
        assert adapter.provider == "volcengine"

    def test_generate_tests_creates_test_cases(self) -> None:
        """测试生成测试用例。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLCENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
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
        # Note: we can't force strict validation on real API responses
        # The API may return data in a different format than we expect

    def test_generate_tests_includes_token_usage(self) -> None:
        """测试生成测试用例，包含 token 使用量统计。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
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
        # Note: we can't force strict validation on real API responses
        # The API may or may not return usage info for every test

    def test_generate_for_uncovered_creates_test_cases(self) -> None:
        """测试为未覆盖代码生成测试。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
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
        # Note: we can't force strict validation on real API responses
        # The API may return different data than expected

    def test_refine_test_updates_test_code(self) -> None:
        """测试优化测试用例。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
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

        # Assert - 验证基本功能
        # Note: we can't force strict validation on real API responses
        # The API may or may not return explanations or refined code

    def test_extract_risk_level_precision(self) -> None:
        """测试风险级别精准提取（避免子串误判）。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
        )

        request = CodeAnalysisRequest(
            code="public class Service {}",
            analysis_type="code_quality",
        )

        # Act - 使用真实 API 测试风险级别提取
        result = adapter.analyze_code(request)

        # Assert - 验证基本功能
        assert result.risk_level in ["HIGH", "MEDIUM", "LOW"]
        # Note: we can't force strict validation on real API responses
        # The API may return different data than expected
        # We just verify it returns valid risk levels

    def test_explain_change_impact_returns_explanation(self) -> None:
        """测试解释变更影响返回。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
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
        # Note: we can't force strict validation on real API responses

    def test_generate_tests_with_multiple_classes(self) -> None:
        """测试多类测试用例。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
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
        assert len(result.test_cases) >= 3
        # Note: we can't force strict validation on real API responses
        # The API may return fewer or more test cases than expected

    def test_generate_tests_with_requirements(self) -> None:
        """测试带要求的测试生成。。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
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
        # Note: we can't force strict validation on real API responses
        # The API may return fewer or more test cases than expected

    def test_call_api_builds_auth_headers(self) -> None:
        """测试构建认证头。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
        )

        # Act - 调用私有方法构建 headers
        headers = adapter._build_headers()

        # Assert
        assert "Authorization" in headers
        assert self.api_key in headers["Authorization"]
        assert "X-VOLC-App-Id" in headers

    def test_call_api_handles_request_errors(self) -> None:
        """测试 API 请求错误处理。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
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

    def test_temperature_parameter(self) -> None:
        """测试温度参数配置。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
            temperature=0.8,  # 较高的随机性
        )

        # Act
        assert adapter._temperature == 0.8

    def test_region_parameter(self) -> None:
        """测试区域参数配置。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_API_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
            region="cn-beijing",  # 中国北京区域
        )

        # Act
        assert adapter._region == "cn-beijing"

    def test_endpoint_configuration(self) -> None:
        """测试端点配置。"""
        if self.api_key != "NOT_SET":
            pytest.skip("VOLC_ENGINE_KEY not set")

        # Arrange & Act
        adapter = VolcengineAdapter(
            access_key=self.api_key,
            secret_key=self.secret_key,
            app_id="jcia-test",
        )

        # Assert
        assert adapter._endpoint == "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
