"""Tests for OpenAI adapter module.

This module provides comprehensive test coverage for the OpenAI adapter,
including test generation, code analysis, and API interaction.
"""

from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from jcia.adapters.ai.openai_adapter import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT,
    OpenAIAdapter,
)
from jcia.core.entities.test_case import TestPriority, TestType
from jcia.core.interfaces.ai_service import (
    AIProvider,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    TestGenerationRequest,
    TestGenerationResponse,
)


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
            "choices": [
                {
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
                }
            ],
            "usage": {"total_tokens": 500},
        }

        test_cases = self.adapter._parse_test_generation_response(response, ["com.example.Service"])

        assert len(test_cases) == 1
        assert test_cases[0].class_name == "com.example.ServiceTest"
        assert test_cases[0].target_class == "com.example.Service"
        assert test_cases[0].test_type == TestType.UNIT
        assert test_cases[0].priority == TestPriority.HIGH

    def test_extract_java_code_from_response(self):
        """Test extracting Java code from response."""
        response = {
            "choices": [
                {
                    "message": {
                        "content": """
Here is the code:
```java
public class Test {}
```
"""
                    }
                }
            ]
        }

        code = self.adapter._extract_java_code_from_response(response)
        assert "public class Test" in code


class TestOpenAIAdapterCodeAnalysis:
    """Tests for code analysis functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = OpenAIAdapter(api_key="test-key")

    @patch.object(OpenAIAdapter, "_call_openai_api")
    def test_analyze_code_success(self, mock_call_api):
        """Test successful code analysis."""
        mock_call_api.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """
潜在问题: Null pointer dereference
风险级别: HIGH
"""
                    }
                }
            ],
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

    @patch.object(OpenAIAdapter, "_call_openai_api")
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

    @patch.object(OpenAIAdapter, "_call_openai_api")
    def test_explain_change_impact_success(self, mock_call_api):
        """Test successful impact explanation."""
        mock_call_api.return_value = {
            "choices": [
                {"message": {"content": "This change affects the user authentication module."}}
            ],
        }

        result = self.adapter.explain_change_impact(
            changed_methods=["com.example.Service.method1"],
            context={"branch": "feature/test"},
        )

        assert "authentication" in result

    @patch.object(OpenAIAdapter, "_call_openai_api")
    def test_explain_change_impact_failure(self, mock_call_api):
        """Test impact explanation failure handling."""
        mock_call_api.side_effect = Exception("API Error")

        result = self.adapter.explain_change_impact(
            changed_methods=["com.example.Service.method1"],
        )

        assert "影响分析失败" in result


class TestOpenAIAdapterMockMode:
    """Tests for mock mode when openai is not installed."""

    @patch.object(OpenAIAdapter, "_call_openai_api")
    def test_generate_tests_with_mock(self, mock_call_api):
        """Test test generation with mocked API."""
        mock_call_api.return_value = {
            "choices": [
                {
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
                }
            ],
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


class TestGenerateTestsFailure:
    """generate_tests 异常回退分支（143-145）。"""

    @patch.object(OpenAIAdapter, "_call_openai_api")
    def test_generate_tests_api_failure_returns_empty(self, mock_call_api: MagicMock) -> None:
        """API 抛异常时返回空结果并给出失败说明。"""
        mock_call_api.side_effect = Exception("boom")
        adapter = OpenAIAdapter(api_key="k")
        request = TestGenerationRequest(
            target_classes=["com.example.Service"], code_snippets={}, context={}
        )

        response = adapter.generate_tests(request, Path("/tmp/project"))

        assert response.test_cases == []
        assert response.confidence == 0.0
        assert any("生成失败" in e for e in response.explanations)


class TestGenerateForUncovered:
    """generate_for_uncovered 主体（168-209）。"""

    def setup_method(self) -> None:
        self.adapter = OpenAIAdapter(api_key="test-key")

    def test_no_uncovered_segments(self) -> None:
        """无未覆盖段时返回提示且置信度为 1.0。"""
        self.adapter._extract_uncovered_segments = MagicMock(return_value=[])  # type: ignore[method-assign]

        response = self.adapter.generate_for_uncovered({}, Path("/tmp/project"))

        assert response.test_cases == []
        assert response.confidence == 1.0
        assert "没有未覆盖的代码" in response.explanations

    def test_with_uncovered_segments(self) -> None:
        """存在未覆盖段时逐段生成并汇总。"""
        segments = [
            {"class_name": "com.example.A", "code": "x", "lines": [2, 3], "branch": 10},
            {"class_name": "com.example.B", "code": "y", "lines": [5]},
        ]
        self.adapter._extract_uncovered_segments = MagicMock(return_value=segments)  # type: ignore[method-assign]

        tc_a = MagicMock()
        tc_a.metadata = {"confidence": 0.8}
        tc_b = MagicMock()
        tc_b.metadata = {}  # 缺省 confidence -> 0.5
        self.adapter.generate_tests = MagicMock(  # type: ignore[method-assign]
            side_effect=[
                TestGenerationResponse(test_cases=[tc_a], explanations=["a"], confidence=0.8),
                TestGenerationResponse(test_cases=[tc_b], explanations=["b"], confidence=0.5),
            ]
        )

        response = self.adapter.generate_for_uncovered({}, Path("/tmp/project"))

        assert len(response.test_cases) == 2
        assert self.adapter.generate_tests.call_count == 2
        # (0.8 + 0.5) / 2
        assert response.confidence == pytest.approx(0.65)


class TestRefineTest:
    """refine_test 主体（234-278）。"""

    def setup_method(self) -> None:
        self.adapter = OpenAIAdapter(api_key="test-key")

    @patch.object(OpenAIAdapter, "_call_openai_api")
    def test_refine_test_success(self, mock_call_api: MagicMock) -> None:
        """成功优化时写回 test_code/refined/feedback 元数据。"""
        mock_call_api.return_value = {
            "choices": [{"message": {"content": "```java\npublic class T {}\n```"}}]
        }
        test_case = MagicMock()
        test_case.metadata = {"test_code": "old"}

        result = self.adapter.refine_test(test_case, "make it better", Path("/tmp/project"))

        assert result.metadata["refined"] is True
        assert result.metadata["feedback"] == "make it better"
        assert "public class T" in result.metadata["test_code"]

    @patch.object(OpenAIAdapter, "_call_openai_api")
    def test_refine_test_failure(self, mock_call_api: MagicMock) -> None:
        """API 异常时原样返回测试用例。"""
        mock_call_api.side_effect = Exception("network down")
        test_case = MagicMock()
        test_case.metadata = {"test_code": "old"}

        result = self.adapter.refine_test(test_case, "feedback", Path("/tmp/project"))

        assert result is test_case
        assert "refined" not in result.metadata


class TestBuildContextAndPromptBranches:
    """_build_generation_context / _build_test_generation_prompt 分支（503-505, 532-534）。"""

    def setup_method(self) -> None:
        self.adapter = OpenAIAdapter(api_key="test-key")

    def test_build_generation_context_with_src(self, tmp_path: Path) -> None:
        """src/main/java 存在时写入 src_structure。"""
        src = tmp_path / "src" / "main" / "java"
        src.mkdir(parents=True)
        request = TestGenerationRequest(target_classes=["A"], code_snippets={}, context={})

        context = self.adapter._build_generation_context(request, tmp_path)

        assert context["src_structure"] == str(src)

    def test_build_generation_context_without_src(self, tmp_path: Path) -> None:
        """目录存在但无 src/main/java 时不含 src_structure。"""
        request = TestGenerationRequest(target_classes=["A"], code_snippets={}, context={})

        context = self.adapter._build_generation_context(request, tmp_path)

        assert "src_structure" not in context
        assert context["project_path"] == str(tmp_path)

    def test_build_prompt_with_dependencies(self) -> None:
        """context 含 dependencies 时追加依赖信息段。"""
        request = TestGenerationRequest(
            target_classes=["A"], code_snippets={}, context={}, requirements=None
        )
        context = {"dependencies": ["lib-1", "lib-2"]}

        prompt = self.adapter._build_test_generation_prompt(request, context)

        assert "## 依赖信息" in prompt
        assert "lib-1" in prompt


class TestUncoveredSegmentsAndSourceFile:
    """_extract_uncovered_segments（661-694）与 _find_source_file（707-715）。"""

    def setup_method(self) -> None:
        self.adapter = OpenAIAdapter(api_key="test-key")

    def test_find_source_file_found(self, tmp_path: Path) -> None:
        """源文件存在时返回其路径。"""
        java_file = tmp_path / "src" / "main" / "java" / "com" / "example" / "Service.java"
        java_file.parent.mkdir(parents=True)
        java_file.write_text("class Service {}")

        found = self.adapter._find_source_file("com.example.Service", tmp_path)

        assert found == java_file

    def test_find_source_file_missing(self, tmp_path: Path) -> None:
        """源文件不存在时返回 None。"""
        assert self.adapter._find_source_file("com.example.Missing", tmp_path) is None

    def test_extract_uncovered_segments(self, tmp_path: Path) -> None:
        """line_coverage<100 且存在未覆盖行时生成代码段。"""
        java_file = tmp_path / "src" / "main" / "java" / "com" / "example" / "Service.java"
        java_file.parent.mkdir(parents=True)
        java_file.write_text("line1\nline2\nline3\nline4\n")
        coverage_data = {
            "classes": [
                {
                    "name": "com.example.Service",
                    "line_coverage": 50,
                    "lines": [1, 0, 0, 1],
                    "branch_coverage": 0,
                }
            ]
        }

        segments = self.adapter._extract_uncovered_segments(coverage_data, tmp_path)

        assert len(segments) == 1
        assert segments[0]["class_name"] == "com.example.Service"
        assert segments[0]["lines"] == [2, 3]

    def test_extract_uncovered_segments_fully_covered(self, tmp_path: Path) -> None:
        """line_coverage==100 的类被跳过。"""
        coverage_data = {"classes": [{"name": "A", "line_coverage": 100, "lines": [1]}]}

        assert self.adapter._extract_uncovered_segments(coverage_data, tmp_path) == []

    def test_extract_uncovered_segments_no_source_file(self, tmp_path: Path) -> None:
        """找不到源文件时不生成段。"""
        coverage_data = {
            "classes": [{"name": "com.example.Nope", "line_coverage": 10, "lines": [0, 0]}]
        }

        assert self.adapter._extract_uncovered_segments(coverage_data, tmp_path) == []


def _fake_openai_module(create: MagicMock) -> ModuleType:
    """构造一个可控的假 openai 模块（含异常类与客户端工厂）。"""
    mod = ModuleType("openai")

    class APIError(Exception):
        pass

    class APITimeoutError(Exception):
        pass

    class RateLimitError(Exception):
        pass

    mod.APIError = APIError  # type: ignore[attr-defined]
    mod.APITimeoutError = APITimeoutError  # type: ignore[attr-defined]
    mod.RateLimitError = RateLimitError  # type: ignore[attr-defined]

    client = MagicMock()
    client.chat.completions.create = create
    mod.OpenAI = MagicMock(return_value=client)  # type: ignore[attr-defined]
    mod._exc = (APIError, APITimeoutError, RateLimitError)  # type: ignore[attr-defined]
    return mod


class TestCallOpenAIModuleMissing:
    """_call_openai_api 中 openai 缺失回退（431-438）。"""

    def test_import_error_returns_mock_response(self) -> None:
        """openai 未安装时返回内置 mock 响应。"""
        adapter = OpenAIAdapter(api_key="k")
        with patch.dict("sys.modules", {"openai": None}):
            result = adapter._call_openai_api([{"role": "user", "content": "hi"}])

        assert "Mock response" in result["choices"][0]["message"]["content"]
        assert result["usage"]["total_tokens"] == 100


class TestCallOpenAIRealClient:
    """_call_openai_api 真实客户端路径（440-483）。"""

    def test_successful_call(self) -> None:
        """成功返回并归一化 usage。"""
        resp = MagicMock()
        resp.usage.prompt_tokens = 11
        resp.usage.completion_tokens = 22
        resp.usage.total_tokens = 33
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = "hello"
        create = MagicMock(return_value=resp)
        mod = _fake_openai_module(create)

        adapter = OpenAIAdapter(api_key="k")
        with patch.dict("sys.modules", {"openai": mod}):
            result = adapter._call_openai_api([{"role": "user", "content": "hi"}])

        assert result["choices"][0]["message"]["content"] == "hello"
        assert result["usage"]["total_tokens"] == 33

    def test_timeout_retries_then_raises(self) -> None:
        """持续超时：重试后最终抛 RuntimeError。"""
        mod = _fake_openai_module(MagicMock())
        mod.OpenAI.return_value.chat.completions.create.side_effect = mod.APITimeoutError(  # type: ignore[attr-defined]
            "timeout"
        )

        adapter = OpenAIAdapter(api_key="k")
        with (
            patch.dict("sys.modules", {"openai": mod}),
            patch("jcia.adapters.ai.openai_adapter.time.sleep") as mock_sleep,
            pytest.raises(RuntimeError, match="timed out"),
        ):
            adapter._call_openai_api([{"role": "user", "content": "hi"}])

        assert mock_sleep.call_count == 2

    def test_rate_limit_retries_then_raises(self) -> None:
        """持续限流：重试后最终抛 RuntimeError。"""
        mod = _fake_openai_module(MagicMock())
        mod.OpenAI.return_value.chat.completions.create.side_effect = mod.RateLimitError(  # type: ignore[attr-defined]
            "slow down"
        )

        adapter = OpenAIAdapter(api_key="k")
        with (
            patch.dict("sys.modules", {"openai": mod}),
            patch("jcia.adapters.ai.openai_adapter.time.sleep") as mock_sleep,
            pytest.raises(RuntimeError, match="rate limit"),
        ):
            adapter._call_openai_api([{"role": "user", "content": "hi"}])

        assert mock_sleep.call_count == 2

    def test_api_error_raises_immediately(self) -> None:
        """一般 API 错误：不重试直接抛 RuntimeError。"""
        mod = _fake_openai_module(MagicMock())
        mod.OpenAI.return_value.chat.completions.create.side_effect = mod.APIError("bad")  # type: ignore[attr-defined]

        adapter = OpenAIAdapter(api_key="k")
        with (
            patch.dict("sys.modules", {"openai": mod}),
            patch("jcia.adapters.ai.openai_adapter.time.sleep") as mock_sleep,
            pytest.raises(RuntimeError, match="API error"),
        ):
            adapter._call_openai_api([{"role": "user", "content": "hi"}])

        assert mock_sleep.call_count == 0


# Mark all tests in this module
pytestmark = pytest.mark.unit
