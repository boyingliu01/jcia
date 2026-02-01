"""火山引擎LLM适配器单元测试."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import requests

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

StubFn = Callable[[VolcengineAdapter, str | None, int | None], None]


@pytest.fixture
def adapter() -> VolcengineAdapter:
    return VolcengineAdapter(
        access_key=TEST_ACCESS_KEY,
        secret_key=TEST_SECRET_KEY,
        app_id=TEST_APP_ID,
    )


@pytest.fixture
def stub_call_api() -> Any:
    def _stub(
        adapter_instance: VolcengineAdapter,
        content: str | None = "stub",
        tokens: int | None = 120,
    ) -> None:
        adapter_instance._call_api = lambda *args, **kwargs: {  # type: ignore[assignment]
            "choices": [{"message": {"content": content or ""}}],
            "usage": {"total_tokens": tokens or 0},
        }

    return _stub


class TestVolcengineAdapter:
    """VolcengineAdapter 测试类."""

    def test_provider_returns_volcengine(self, adapter: VolcengineAdapter) -> None:
        """测试提供商返回火山引擎."""
        assert adapter.provider == AIProvider.OPENAI  # 暂时使用OPENAI标识

    def test_model_returns_default_model(self, adapter: VolcengineAdapter) -> None:
        """测试默认模型名称."""
        assert adapter.model == "doubao-pro-32k"

    def test_model_returns_custom_model(self) -> None:
        """测试自定义模型名称."""
        custom = VolcengineAdapter(
            access_key=TEST_ACCESS_KEY,
            secret_key=TEST_SECRET_KEY,
            app_id=TEST_APP_ID,
            model="doubao-pro-128k",
        )

        assert custom.model == "doubao-pro-128k"

    def test_generate_tests_creates_test_cases(
        self,
        adapter: VolcengineAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试生成测试用例."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={
                "com.example.Service": "public class Service { public void method() {} }"
            },
            context={"project_path": "/fake/project"},
        )
        stub_call_api(adapter, content="// generated test", tokens=120)

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) > 0
        assert response.test_cases[0].class_name == "com.example.ServiceTest"
        assert len(response.explanations) > 0

    def test_generate_tests_includes_token_usage(
        self,
        adapter: VolcengineAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试生成测试包含token使用统计."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={"com.example.Service": "class Service {}"},
            context={},
        )
        stub_call_api(adapter, tokens=500, content=None)

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert response.tokens_used >= 0
        assert 0.0 <= response.confidence <= 1.0

    def test_generate_for_uncovered_creates_tests(
        self,
        adapter: VolcengineAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试为未覆盖代码生成测试."""
        coverage_data = {
            "uncovered_classes": ["com.example.UncoveredClass"],
            "uncovered_methods": [],
        }
        stub_call_api(adapter, content=None, tokens=50)

        # Act
        response = adapter.generate_for_uncovered(coverage_data, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) > 0

    def test_refine_test_updates_test_code(
        self,
        adapter: VolcengineAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试优化测试用例."""
        test_case = TestCase(
            class_name="ServiceTest",
            method_name="testMethod",
            metadata={"test_code": "原始测试代码"},
        )
        stub_call_api(adapter, content="新测试代码", tokens=120)

        # Act
        refined = adapter.refine_test(test_case, "测试不够全面", Path("/fake/project"))

        # Assert
        assert isinstance(refined, TestCase)

    def test_analyze_code_returns_analysis(
        self,
        adapter: VolcengineAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试代码分析."""
        request = CodeAnalysisRequest(code="public class Service {}", analysis_type="code_quality")
        stub_call_api(adapter, content="Risk HIGH with suggestion", tokens=80)

        # Act
        response = adapter.analyze_code(request)

        # Assert
        assert len(response.findings) > 0
        assert len(response.suggestions) > 0
        assert response.risk_level in ["HIGH", "MEDIUM", "LOW"]

    def test_explain_change_impact_returns_explanation(
        self,
        adapter: VolcengineAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试解释变更影响."""
        stub_call_api(adapter, content="影响说明", tokens=60)

        explanation = adapter.explain_change_impact(changed_methods=["com.Service.method1"])

        assert isinstance(explanation, str)

    def test_generate_tests_with_multiple_classes(
        self,
        adapter: VolcengineAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试为多个类生成测试."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service1", "com.example.Service2"],
            code_snippets={
                "com.example.Service1": "class Service1 {}",
                "com.example.Service2": "class Service2 {}",
            },
            context={},
        )
        stub_call_api(adapter, content="multi", tokens=70)

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) == 2

    def test_generate_tests_with_requirements(
        self,
        adapter: VolcengineAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试带要求的测试生成."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={"com.example.Service": "class Service {}"},
            context={},
            requirements="生成边界条件测试",
        )
        stub_call_api(adapter, content="req", tokens=90)

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) > 0

    @patch("jcia.adapters.ai.volcengine_adapter.requests.post")
    def test_call_api_builds_auth_headers(self, mock_post, adapter: VolcengineAdapter) -> None:
        """验证 _call_api 使用 AK/SK/AppId/Region 头并包含 app_id."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}], "usage": {}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        adapter._call_api([{"role": "user", "content": "hi"}])

        called_args, called_kwargs = mock_post.call_args
        assert called_args[0] == adapter._endpoint
        headers = called_kwargs["headers"]
        payload = called_kwargs["json"]
        assert headers["Authorization"].startswith("VolcengineAK ")
        assert TEST_ACCESS_KEY in headers["Authorization"]
        assert TEST_SECRET_KEY in headers["Authorization"]
        assert headers["X-Volc-App-Id"] == TEST_APP_ID
        assert headers["X-Volc-Region"] == adapter._region
        assert payload["app_id"] == TEST_APP_ID

    @patch(
        "jcia.adapters.ai.volcengine_adapter.requests.post",
        side_effect=requests.exceptions.RequestException("boom"),
    )
    def test_call_api_handles_request_errors(self, mock_post, adapter: VolcengineAdapter) -> None:
        """请求异常时返回空响应结构。"""
        result = adapter._call_api([{"role": "user", "content": "hi"}])

        assert result.get("choices")
        assert result.get("usage") == {}
        mock_post.assert_called_once()
