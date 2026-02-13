"""OpenAI 适配器单元测试."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from jcia.adapters.ai.openai_adapter import OpenAIAdapter
from jcia.core.entities.test_case import TestCase
from jcia.core.interfaces.ai_service import (
    AIProvider,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    TestGenerationRequest,
)

TEST_API_KEY = "test-key"

StubFn = Callable[[OpenAIAdapter, str | None, int | None], None]


@pytest.fixture
def adapter() -> OpenAIAdapter:
    return OpenAIAdapter(api_key=TEST_API_KEY)


@pytest.fixture
def stub_call_api() -> Any:
    def _stub(
        adapter_instance: OpenAIAdapter,
        content: str | None = "stub",
        tokens: int | None = 120,
    ) -> None:
        adapter_instance._call_openai_api = lambda *args, **kwargs: {  # type: ignore[assignment]
            "choices": [{"message": {"content": content or ""}}],
            "usage": {"total_tokens": tokens or 0},
        }

    return _stub


class TestOpenAIAdapter:
    """OpenAIAdapter 测试类."""

    def test_provider_returns_openai(self, adapter: OpenAIAdapter) -> None:
        """测试提供商返回 OpenAI."""
        assert adapter.provider == AIProvider.OPENAI

    def test_model_returns_default_model(self, adapter: OpenAIAdapter) -> None:
        """测试默认模型名称."""
        assert adapter.model == "gpt-4-turbo-preview"

    def test_model_returns_custom_model(self) -> None:
        """测试自定义模型名称."""
        custom = OpenAIAdapter(
            api_key=TEST_API_KEY,
            model="gpt-4",
        )

        assert custom.model == "gpt-4"

    def test_base_url_returns_default(self, adapter: OpenAIAdapter) -> None:
        """测试默认 base_url."""
        assert adapter._base_url == "https://api.openai.com/v1"

    def test_base_url_returns_custom(self) -> None:
        """测试自定义 base_url."""
        custom = OpenAIAdapter(
            api_key=TEST_API_KEY,
            base_url="https://custom.openai.com/v1",
        )

        assert custom._base_url == "https://custom.openai.com/v1"

    def test_temperature_and_max_tokens(self) -> None:
        """测试温度和最大 token 参数."""
        adapter = OpenAIAdapter(
            api_key=TEST_API_KEY,
            temperature=0.5,
            max_tokens=2048,
        )

        assert adapter._temperature == 0.5
        assert adapter._max_tokens == 2048

    def test_generate_tests_creates_test_cases(
        self,
        adapter: OpenAIAdapter,
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
        test_code = (
            "```java\npublic class ServiceTest {\n"
            "    @Test\n    public void testMethod() {}\n}\n```"
        )
        stub_call_api(adapter, content=test_code, tokens=120)

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) > 0
        assert response.test_cases[0].class_name == "com.example.ServiceTest"
        assert len(response.explanations) > 0

    def test_generate_tests_with_multiple_classes(
        self,
        adapter: OpenAIAdapter,
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
        stub_call_api(
            adapter,
            content="""```java
public class Service1Test { @Test public void testMethod1() {} }
```
```java
public class Service2Test { @Test public void testMethod2() {} }
```""",
            tokens=70,
        )

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) == 2

    def test_generate_tests_includes_token_usage(
        self,
        adapter: OpenAIAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试生成测试包含token使用统计."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={"com.example.Service": "class Service {}"},
            context={},
        )
        stub_call_api(adapter, tokens=500, content="```java\nclass Test {}\n```")

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert response.tokens_used >= 0
        assert 0.0 <= response.confidence <= 1.0

    def test_generate_tests_with_requirements(
        self,
        adapter: OpenAIAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试带要求的测试生成."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={"com.example.Service": "class Service {}"},
            context={},
            requirements="生成边界条件测试",
        )
        stub_call_api(adapter, content="```java\nreq\n```", tokens=90)

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert len(response.test_cases) > 0

    def test_generate_tests_handles_exception(self, adapter: OpenAIAdapter) -> None:
        """测试生成测试处理异常."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={"com.example.Service": "class Service {}"},
            context={},
        )

        # Mock to raise exception
        adapter._call_openai_api = MagicMock(side_effect=RuntimeError("API Error"))  # type: ignore[assignment]

        # Act
        response = adapter.generate_tests(request, Path("/fake/project"))

        # Assert
        assert response.test_cases == []
        assert response.confidence == 0.0
        assert "生成失败" in response.explanations[0]

    def test_generate_for_uncovered_creates_tests(
        self,
        adapter: OpenAIAdapter,
        stub_call_api: Any,
        tmp_path: Path,
    ) -> None:
        """测试为未覆盖代码生成测试."""
        # Create source file
        src_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
        src_dir.mkdir(parents=True, exist_ok=True)
        java_file = src_dir / "UncoveredClass.java"
        java_file.write_text("""
package com.example;
public class UncoveredClass {
    public void method1() {}
    public void method2() {}
}
""")

        coverage_data = {
            "classes": [
                {
                    "name": "com.example.UncoveredClass",
                    "line_coverage": 50,
                    "lines": [0, 1, 0, 1],
                }
            ]
        }
        stub_call_api(adapter, content="```java\nclass Test {}\n```", tokens=50)

        # Act
        response = adapter.generate_for_uncovered(coverage_data, tmp_path)

        # Assert
        assert len(response.test_cases) > 0

    def test_generate_for_uncovered_no_uncovered(self, adapter: OpenAIAdapter) -> None:
        """测试没有未覆盖代码时返回空结果."""
        coverage_data = {"classes": []}

        # Act
        response = adapter.generate_for_uncovered(coverage_data, Path("/fake/project"))

        # Assert
        assert response.test_cases == []
        assert response.confidence == 1.0
        assert "没有未覆盖的代码" in response.explanations[0]

    def test_refine_test_updates_test_code(
        self,
        adapter: OpenAIAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试优化测试用例."""
        test_case = TestCase(
            class_name="ServiceTest",
            method_name="testMethod",
            metadata={"test_code": "原始测试代码"},
        )
        stub_call_api(adapter, content="```java\n新测试代码\n```", tokens=120)

        # Act
        refined = adapter.refine_test(test_case, "测试不够全面", Path("/fake/project"))

        # Assert
        assert isinstance(refined, TestCase)
        assert refined.metadata.get("refined") is True
        assert refined.metadata.get("feedback") == "测试不够全面"

    def test_refine_test_handles_exception(
        self, adapter: OpenAIAdapter
    ) -> None:
        """测试优化测试用例处理异常."""
        test_case = TestCase(
            class_name="ServiceTest",
            method_name="testMethod",
            metadata={"test_code": "原始测试代码"},
        )

        # Mock to raise exception
        adapter._call_openai_api = MagicMock(side_effect=RuntimeError("API Error"))  # type: ignore[assignment]

        # Act
        refined = adapter.refine_test(test_case, "测试不够全面", Path("/fake/project"))

        # Assert
        assert isinstance(refined, TestCase)
        assert refined.metadata.get("test_code") == "原始测试代码"

    def test_analyze_code_returns_response(
        self,
        adapter: OpenAIAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试代码分析返回响应."""
        request = CodeAnalysisRequest(
            code="public class Test {}",
            analysis_type="quality",
        )
        stub_call_api(adapter, content="风险级别: HIGH", tokens=60)

        # Act
        response = adapter.analyze_code(request)

        # Assert
        assert isinstance(response, CodeAnalysisResponse)
        assert response.risk_level == "HIGH"

    def test_analyze_code_handles_exception(
        self, adapter: OpenAIAdapter
    ) -> None:
        """测试代码分析处理异常."""
        request = CodeAnalysisRequest(
            code="public class Test {}",
            analysis_type="quality",
        )

        # Mock to raise exception
        adapter._call_openai_api = MagicMock(side_effect=RuntimeError("API Error"))  # type: ignore[assignment]

        # Act
        response = adapter.analyze_code(request)

        # Assert
        assert response.risk_level == "HIGH"
        assert "分析失败" in response.findings[0]["content"]

    def test_explain_change_impact_returns_explanation(
        self,
        adapter: OpenAIAdapter,
        stub_call_api: Any,
    ) -> None:
        """测试解释变更影响."""
        stub_call_api(adapter, content="影响说明", tokens=60)

        explanation = adapter.explain_change_impact(changed_methods=["com.Service.method1"])

        assert isinstance(explanation, str)

    def test_explain_change_impact_handles_exception(
        self, adapter: OpenAIAdapter
    ) -> None:
        """测试解释变更影响处理异常."""
        # Mock to raise exception
        adapter._call_openai_api = MagicMock(side_effect=RuntimeError("API Error"))  # type: ignore[assignment]

        explanation = adapter.explain_change_impact(changed_methods=["com.Service.method1"])

        assert "影响分析失败" in explanation

    def test_extract_risk_level_precision(self, adapter: OpenAIAdapter) -> None:
        """测试风险等级提取的精准度（避免子串误判）."""
        assert adapter._extract_risk_level("The status is LOWPASS") == "MEDIUM"
        assert adapter._extract_risk_level("Risk is HIGH now") == "HIGH"
        assert adapter._extract_risk_level("This is a LOW risk") == "LOW"
        assert adapter._extract_risk_level("Default medium") == "MEDIUM"

    def test_extract_all_java_code_blocks(self, adapter: OpenAIAdapter) -> None:
        """测试提取所有 Java 代码块."""
        content = """
```java
public class Test1 {}
```

Some text

```java
public class Test2 {}
```
"""
        blocks = adapter._extract_all_java_code_blocks(content)

        assert len(blocks) == 2
        assert "class Test1" in blocks[0]
        assert "class Test2" in blocks[1]

    def test_extract_test_methods(self, adapter: OpenAIAdapter) -> None:
        """测试提取测试方法名."""
        test_code = """
@Test
public void testMethod1() {}

@Test
public void testMethod2() {}
"""
        methods = adapter._extract_test_methods(test_code)

        assert methods == ["testMethod1", "testMethod2"]

    def test_estimate_confidence(self, adapter: OpenAIAdapter) -> None:
        """测试置信度估算."""
        # 测试不同 token 数量的置信度
        assert adapter._estimate_confidence({"usage": {"total_tokens": 50}}) == 0.3
        assert adapter._estimate_confidence({"usage": {"total_tokens": 300}}) == 0.5
        assert adapter._estimate_confidence({"usage": {"total_tokens": 700}}) == 0.7
        assert adapter._estimate_confidence({"usage": {"total_tokens": 1500}}) == 0.9

    def test_parse_code_findings(self, adapter: OpenAIAdapter) -> None:
        """测试解析代码分析结果."""
        content = "潜在问题: 空指针风险\n潜在问题: 资源未关闭"
        findings = adapter._parse_code_findings(content)

        assert len(findings) == 2
        assert "空指针风险" in findings[0]["content"]
        assert "资源未关闭" in findings[1]["content"]

    def test_parse_code_suggestions(self, adapter: OpenAIAdapter) -> None:
        """测试解析代码改进建议."""
        content = "改进建议: 添加空值检查\n改进建议: 使用 try-with-resources"
        suggestions = adapter._parse_code_suggestions(content)

        assert len(suggestions) == 2
        assert "添加空值检查" in suggestions[0]
        assert "使用 try-with-resources" in suggestions[1]

    def test_build_generation_context(self, adapter: OpenAIAdapter) -> None:
        """测试构建生成上下文."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={"com.example.Service": "class Service {}"},
            context={},
        )

        context = adapter._build_generation_context(request, Path("/fake/project"))

        # Use str() to handle Windows/Unix path differences
        assert "fake" in str(context["project_path"])
        assert "project" in str(context["project_path"])

    def test_build_test_generation_prompt(self, adapter: OpenAIAdapter) -> None:
        """测试构建测试生成 prompt."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={"com.example.Service": "class Service {}"},
            context={},
            requirements="生成边界测试",
        )

        prompt = adapter._build_test_generation_prompt(request, {})

        assert "com.example.Service" in prompt
        assert "class Service {}" in prompt
        assert "生成边界测试" in prompt

    def test_parse_test_generation_response(self, adapter: OpenAIAdapter) -> None:
        """测试解析测试生成响应."""
        response = {
            "choices": [
                {
                    "message": {
                        "content": "```java\n@Test\npublic void testMethod() {}\n```"
                    }
                }
            ]
        }
        target_classes = ["com.example.Service"]

        test_cases = adapter._parse_test_generation_response(response, target_classes)

        assert len(test_cases) == 1
        assert test_cases[0].class_name == "com.example.ServiceTest"
        assert test_cases[0].method_name == "testMethod"
