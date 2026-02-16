"""Tests for OpenAI adapter module.

This module provides comprehensive test coverage for the OpenAI adapter,
including test generation, code analysis, and API interaction.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest

from jcia.adapters.ai.openai_adapter import (
    OpenAIAdapter,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
)
from jcia.core.interfaces.ai_service import (
    AIProvider,
    TestGenerationRequest,
    TestGenerationResponse,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
)
from jcia.core.entities.test_case import TestCase, TestPriority, TestType


class TestOpenAIAdapterInitialization:
    """Tests for OpenAIAdapter initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        adapter = OpenAIAdapter(api_key="test-key")
        assert adapter._api_key == "test-key"
        assert adapter._model == DEFAULT_MODEL
        assert adapter._temperature == DEFAULT_TEMPERATURE
        assert adapter._max_tokens == DEFAULT_MAX_TOKENS
        assert adapter._timeout == DEFAULT_TIMEOUT
        assert adapter._base_url == "https://api.openai.com/v1"

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        adapter = OpenAIAdapter(
            api_key="custom-key",
            model="gpt-3.5-turbo",
            base_url="https://custom.api.com",
            temperature=0.5,
            max_tokens=2048,
            timeout=120,
        )
        assert adapter._api_key == "custom-key"
        assert adapter._model == "gpt-3.5-turbo"
        assert adapter._base_url == "https://custom.api.com"
        assert adapter._temperature == 0.5
        assert adapter._max_tokens == 2048
        assert adapter._timeout == 120

    def test_provider_property(self):
        """Test provider property returns OPENAI."""
        adapter = OpenAIAdapter(api_key="test-key")
        assert adapter.provider == AIProvider.OPENAI

    def test_model_property(self):
        """Test model property returns the model name."""
        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")
        assert adapter.model == "gpt-4"


class TestOpenAIAdapterPrivateMethods:
    """Tests for OpenAIAdapter private helper methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = OpenAIAdapter(api_key="test-key")

    def test_extract_all_java_code_blocks(self):
        """Test extracting Java code blocks from content."""
        content = """
Here is the test code:
```java
public class Test {
    @Test
    void testMethod() {}
}
```
And another:
```java
class AnotherTest {}
```
"""
        blocks = self.adapter._extract_all_java_code_blocks(content)
        assert len(blocks) == 2
        assert "public class Test" in blocks[0]
        assert "class AnotherTest" in blocks[1]

    def test_extract_all_java_code_blocks_no_blocks(self):
        """Test extracting Java code blocks when none exist."""
        content = "No code blocks here"
        blocks = self.adapter._extract_all_java_code_blocks(content)
        assert blocks == ["No code blocks here"]

    def test_extract_test_methods(self):
        """Test extracting test method names from code."""
        code = """
@Test
void testMethod1() {}
@Test
public void testMethod2() {}
private void helper() {}
"""
        methods = self.adapter._extract_test_methods(code)
        assert "testMethod1" in methods
        assert "testMethod2" in methods
        assert "helper" not in methods

    def test_estimate_confidence_low(self):
        """Test confidence estimation for low token count."""
        response = {"usage": {"total_tokens": 50}}
        confidence = self.adapter._estimate_confidence(response)
        assert confidence == 0.3

    def test_estimate_confidence_medium_low(self):
        """Test confidence estimation for medium-low token count."""
        response = {"usage": {"total_tokens": 300}}
        confidence = self.adapter._estimate_confidence(response)
        assert confidence == 0.5

    def test_estimate_confidence_medium_high(self):
        """Test confidence estimation for medium-high token count."""
        response = {"usage": {"total_tokens": 700}}
        confidence = self.adapter._estimate_confidence(response)
        assert confidence == 0.7

    def test_estimate_confidence_high(self):
        """Test confidence estimation for high token count."""
        response = {"usage": {"total_tokens": 1500}}
        confidence = self.adapter._estimate_confidence(response)
        assert confidence == 0.9

    def test_extract_risk_level_high(self):
        """Test extracting HIGH risk level."""
        content = "The risk level is HIGH for this code"
        level = self.adapter._extract_risk_level(content)
        assert level == "HIGH"

    def test_extract_risk_level_low(self):
        """Test extracting LOW risk level."""
        content = "This code has LOW risk"
        level = self.adapter._extract_risk_level(content)
        assert level == "LOW"

    def test_extract_risk_level_medium_default(self):
        """Test default MEDIUM risk level."""
        content = "No explicit risk level mentioned"
        level = self.adapter._extract_risk_level(content)
        assert level == "MEDIUM"

    def test_parse_code_findings(self):
        """Test parsing code analysis findings."""
        content = """
潜在问题: Null pointer risk
潜在问题: Resource leak
"""
        findings = self.adapter._parse_code_findings(content)
        assert len(findings) == 2
        assert findings[0]["content"] == "Null pointer risk"
        assert findings[0]["severity"] == "INFO"

    def test_parse_code_findings_no_issues(self):
        """Test parsing code findings when no issues found."""
        content = "No issues found in this code"
        findings = self.adapter._parse_code_findings(content)
        assert len(findings) == 1
        assert findings[0]["content"] == "No issues found in this code"

    def test_parse_code_suggestions(self):
        """Test parsing code improvement suggestions."""
        content = """
改进建议: Add null check
改进建议: Use try-with-resources
"""
        suggestions = self.adapter._parse_code_suggestions(content)
        assert len(suggestions) == 2
        assert "Add null check" in suggestions
        assert "Use try-with-resources" in suggestions

    def test_parse_code_suggestions_none(self):
        """Test parsing suggestions when none found."""
        content = "No suggestions"
        suggestions = self.adapter._parse_code_suggestions(content)
        assert suggestions == ["请根据代码质量评估进行改进"]


class TestOpenAIAdapterGenerationContext:
    """Tests for generation context building."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = OpenAIAdapter(api_key="test-key")

    def test_build_generation_context(self):
        """Test building generation context."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={},
            context={},
        )
        project_path = Path("/tmp/project")

        context = self.adapter._build_generation_context(request, project_path)

        assert context["project_path"] == str(project_path)

    def test_build_test_generation_prompt(self):
        """Test building test generation prompt."""
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={"com.example.Service": "public class Service {}"},
            context={},
            requirements="Add edge case tests",
        )
        context = {"project_path": "/tmp/project"}

        prompt = self.adapter._build_test_generation_prompt(request, context)

        assert "com.example.Service" in prompt
        assert "Service {}" in prompt
        assert "Add edge case tests" in prompt


class TestOpenAIAdapterResponseParsing:
    """Tests for response parsing methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = OpenAIAdapter(api_key="test-key")

    def test_parse_test_generation_response(self):
        """Test parsing test generation response."""
        response = {
            "choices": [{
                "message": {
                    "content": """
```java
public class ServiceTest {
    @Test
    void testMethod() {}
}
```
"""
                }
            }],
            "usage": {"total_tokens": 500},
        }

        test_cases = self.adapter._parse_test_generation_response(
            response, ["com.example.Service"]
        )

        assert len(test_cases) == 1
        assert test_cases[0].class_name == "com.example.ServiceTest"
        assert test_cases[0].target_class == "com.example.Service"
        assert test_cases[0].test_type == TestType.UNIT
        assert test_cases[0].priority == TestPriority.HIGH

    def test_extract_java_code_from_response(self):
        """Test extracting Java code from response."""
        response = {
            "choices": [{
                "message": {
                    "content": """
Here is the code:
```java
public class Test {}
```
"""
                }
            }]
        }

        code = self.adapter._extract_java_code_from_response(response)
        assert "public class Test" in code


class TestOpenAIAdapterCodeAnalysis:
    """Tests for code analysis functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = OpenAIAdapter(api_key="test-key")

    @patch.object(OpenAIAdapter, '_call_openai_api')
    def test_analyze_code_success(self, mock_call_api):
        """Test successful code analysis."""
        mock_call_api.return_value = {
            "choices": [{
                "message": {
                    "content": """
潜在问题: Null pointer dereference
风险级别: HIGH
"""
                }
            }],
            "usage": {"total_tokens": 800},
        }

        request = CodeAnalysisRequest(
            code="public class Test { void method() { String s = null; s.length(); } }",
            analysis_type="quality",
        )

        response = self.adapter.analyze_code(request)

        assert isinstance(response, CodeAnalysisResponse)
        assert len(response.findings) > 0
        assert response.risk_level == "HIGH"

    @patch.object(OpenAIAdapter, '_call_openai_api')
    def test_analyze_code_failure(self, mock_call_api):
        """Test code analysis failure handling."""
        mock_call_api.side_effect = Exception("API Error")

        request = CodeAnalysisRequest(
            code="public class Test {}",
            analysis_type="quality",
        )

        response = self.adapter.analyze_code(request)

        assert isinstance(response, CodeAnalysisResponse)
        assert len(response.findings) > 0
        assert "分析失败" in response.findings[0]["content"]
        assert response.risk_level == "HIGH"


class TestOpenAIAdapterImpactExplanation:
    """Tests for change impact explanation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = OpenAIAdapter(api_key="test-key")

    @patch.object(OpenAIAdapter, '_call_openai_api')
    def test_explain_change_impact_success(self, mock_call_api):
        """Test successful impact explanation."""
        mock_call_api.return_value = {
            "choices": [{
                "message": {
                    "content": "This change affects the user authentication module."
                }
            }],
        }

        result = self.adapter.explain_change_impact(
            changed_methods=["com.example.Service.method1"],
            context={"branch": "feature/test"},
        )

        assert "authentication" in result

    @patch.object(OpenAIAdapter, '_call_openai_api')
    def test_explain_change_impact_failure(self, mock_call_api):
        """Test impact explanation failure handling."""
        mock_call_api.side_effect = Exception("API Error")

        result = self.adapter.explain_change_impact(
            changed_methods=["com.example.Service.method1"],
        )

        assert "影响分析失败" in result


class TestOpenAIAdapterMockMode:
    """Tests for mock mode when openai is not installed."""

    @patch.object(OpenAIAdapter, '_call_openai_api')
    def test_generate_tests_with_mock(self, mock_call_api):
        """Test test generation with mocked API."""
        mock_call_api.return_value = {
            "choices": [{
                "message": {
                    "content": """
```java
public class ServiceTest {
    @Test
    void testMethod() {}
}
```
"""
                }
            }],
            "usage": {"total_tokens": 500},
        }

        adapter = OpenAIAdapter(api_key="test-key")
        request = TestGenerationRequest(
            target_classes=["com.example.Service"],
            code_snippets={},
            context={},
        )

        response = adapter.generate_tests(request, Path("/tmp/project"))

        assert isinstance(response, TestGenerationResponse)
        assert len(response.test_cases) == 1


# Mark all tests in this module
pytestmark = pytest.mark.unit
