"""OpenAI 适配器实现（修复版）.

基于 OpenAI API 的测试用例生成和代码分析适配器。
"""

import logging
import re
import time
from pathlib import Path
from typing import Any

from jcia.core.entities.test_case import TestCase, TestPriority, TestType
from jcia.core.interfaces.ai_service import (
    AIAnalyzer,
    AIProvider,
    AITestGenerator,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    TestGenerationRequest,
    TestGenerationResponse,
)

logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_MODEL = "gpt-4-turbo-preview"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 2


class OpenAIAdapter(AITestGenerator, AIAnalyzer):
    """OpenAI 服务适配器.

    使用 OpenAI API 提供以下功能：
    - 测试用例生成
    - 代码分析
    - 代码解释
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str | None = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """初始化适配器.

        Args:
            api_key: OpenAI API 密钥
            model: 模型名称（默认 gpt-4-turbo-preview）
            base_url: API 基础 URL（默认使用官方端点）
            temperature: 温度参数（0-1）
            max_tokens: 最大 token 数量
            timeout: 请求超时时间（秒）
        """
        self._api_key = api_key
        self._model = model
        self._base_url = base_url or "https://api.openai.com/v1"  # type: ignore[assignment]
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

        logger.info(f"OpenAIAdapter initialized with model: {self._model}")

    @property
    def provider(self) -> AIProvider:
        """返回 AI 服务提供商."""
        return AIProvider.OPENAI

    @property
    def model(self) -> str:
        """返回使用的模型名称."""
        return self._model

    def generate_tests(
        self,
        request: TestGenerationRequest,
        project_path: Path,
        **kwargs: Any,
    ) -> TestGenerationResponse:
        """使用 AI 生成测试用例.

        Args:
            request: 测试生成请求
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            TestGenerationResponse: 生成响应
        """
        logger.info(f"Generating tests for {len(request.target_classes)} target classes")

        # 构建上下文
        context = self._build_generation_context(request, project_path)

        # 构建 prompt
        messages = [
            {
                "role": "system",
                "content": """你是一个专业的 Java 测试工程师。你的任务是：
1. 为给定的 Java 类生成高质量的单元测试
2. 测试应覆盖所有边界条件和异常情况
3. 使用 JUnit 5 和 Mockito 框架
4. 生成的测试代码应该可以直接编译运行

输出格式：每个测试类使用 ```java``` 代码块包裹。
每个测试方法都应该有清晰的文档注释。""",
            },
            {
                "role": "user",
                "content": self._build_test_generation_prompt(request, context),
            },
        ]

        # 调用 OpenAI API
        try:
            response = self._call_openai_api(
                messages=messages,
                temperature=kwargs.get("temperature", self._temperature),
                max_tokens=kwargs.get("max_tokens", self._max_tokens),
            )

            # 解析响应
            test_cases = self._parse_test_generation_response(response, request.target_classes)

            explanations = [f"为 {cls} 生成测试用例" for cls in request.target_classes]

            confidence = self._estimate_confidence(response)

            return TestGenerationResponse(
                test_cases=test_cases,
                explanations=explanations,
                confidence=confidence,
                tokens_used=response.get("usage", {}).get("total_tokens", 0),
            )

        except Exception as e:
            logger.error(f"Failed to generate tests: {e}")
            return TestGenerationResponse(
                test_cases=[],
                explanations=[f"生成失败: {str(e)}"],
                confidence=0.0,
                tokens_used=0,
            )

    def generate_for_uncovered(
        self,
        coverage_data: dict[str, Any],
        project_path: Path,
        **kwargs: Any,
    ) -> TestGenerationResponse:
        """为未覆盖代码生成测试.

        Args:
            coverage_data: 覆盖率数据
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            TestGenerationResponse: 生成响应
        """
        logger.info("Generating tests for uncovered code")

        # 提取未覆盖的代码段
        uncovered_segments = self._extract_uncovered_segments(coverage_data, project_path)

        if not uncovered_segments:
            return TestGenerationResponse(
                test_cases=[],
                explanations=["没有未覆盖的代码"],
                confidence=1.0,
                tokens_used=0,
            )

        # 为每个未覆盖段生成测试
        all_test_cases = []
        all_explanations = []

        for segment in uncovered_segments:
            request = TestGenerationRequest(
                target_classes=[segment["class_name"]],
                code_snippets={segment["class_name"]: segment["code"]},
                context={
                    "uncovered_lines": segment["lines"],
                    "branch_coverage": segment.get("branch", 0),
                },
                requirements=f"""请为以下代码生成测试，以覆盖第 {segment["lines"]} 行：
重点覆盖未覆盖的分支和条件。
确保测试代码可以直接编译运行。
""",
            )

            response = self.generate_tests(request, project_path, **kwargs)
            all_test_cases.extend(response.test_cases)
            all_explanations.extend(response.explanations)

        confidence = (
            sum(tc.metadata.get("confidence", 0.5) for tc in all_test_cases) / len(all_test_cases)
            if all_test_cases
            else 0.0
        )

        return TestGenerationResponse(
            test_cases=all_test_cases,
            explanations=all_explanations,
            confidence=confidence,
            tokens_used=0,
        )

    def refine_test(
        self,
        test_case: TestCase,
        feedback: str,
        project_path: Path,
        **kwargs: Any,
    ) -> TestCase:
        """根据反馈优化测试用例.

        Args:
            test_case: 原始测试用例
            feedback: 反馈信息
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            TestCase: 优化后的测试用例
        """
        logger.info(f"Refining test case based on feedback: {feedback[:100]}...")

        original_code = test_case.metadata.get("test_code", "")

        prompt = f"""
原始测试用例:
```java
{original_code}
```

反馈意见:
{feedback}

请根据反馈意见优化测试用例，使其更加健壮和全面。
输出格式：使用 ```java``` 代码块包裹优化后的测试代码。
"""

        system_msg = (
            "你是一个专业的测试代码优化助手。请根据反馈意见改进测试用例，确保代码质量和覆盖率。"
        )
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]

        try:
            response = self._call_openai_api(
                messages=messages,
                temperature=kwargs.get("temperature", self._temperature),
            )

            # 提取优化后的代码
            refined_code = self._extract_java_code_from_response(response)

            # 更新测试用例
            test_case.metadata["test_code"] = refined_code
            test_case.metadata["refined"] = True
            test_case.metadata["feedback"] = feedback

            logger.info("Test case refined successfully")

        except Exception as e:
            logger.error(f"Failed to refine test case: {e}")

        return test_case

    def analyze_code(
        self,
        request: CodeAnalysisRequest,
        **kwargs: Any,
    ) -> CodeAnalysisResponse:
        """分析代码.

        Args:
            request: 分析请求
            **kwargs: 额外参数

        Returns:
            CodeAnalysisResponse: 分析响应
        """
        logger.info("Analyzing code")

        prompt = f"""
请分析以下代码:

```java
{request.code}
```

分析类型: {request.analysis_type}

请提供以下信息:
1. 代码质量评估（优秀/良好/一般/需改进）
2. 潜在问题（列表）
3. 改进建议（列表）
4. 风险级别 (HIGH/MEDIUM/LOW)

请以清晰的格式输出分析结果。
"""

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的代码分析助手。请详细分析代码质量、潜在问题和改进建议。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        try:
            response = self._call_openai_api(
                messages=messages,
                temperature=kwargs.get("temperature", 0.3),  # 使用较低的温度以获得更稳定的输出
            )

            # 解析响应
            analysis = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            findings = self._parse_code_findings(analysis)
            suggestions = self._parse_code_suggestions(analysis)
            risk_level = self._extract_risk_level(analysis)

            return CodeAnalysisResponse(
                findings=findings,
                suggestions=suggestions,
                risk_level=risk_level,
            )

        except Exception as e:
            logger.error(f"Failed to analyze code: {e}")
            return CodeAnalysisResponse(
                findings=[{"content": f"分析失败: {str(e)}", "severity": "ERROR"}],
                suggestions=["请检查代码并重试"],
                risk_level="HIGH",
            )

    def explain_change_impact(
        self,
        changed_methods: list[str],
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """解释变更影响.

        Args:
            changed_methods: 变更的方法列表
            context: 上下文信息
            **kwargs: 额外参数

        Returns:
            str: 影响说明
        """
        logger.info(f"Explaining impact for {len(changed_methods)} changed methods")

        methods_str = "\n".join(f"  - {method}" for method in changed_methods)
        context_str = str(context) if context else "无"

        prompt = f"""
请分析以下代码变更的影响范围:

变更的方法:
{methods_str}

上下文信息:
{context_str}

请提供:
1. 变更可能影响的功能模块
2. 需要关注的测试用例
3. 潜在的风险点
4. 建议的测试策略

请以清晰的格式输出分析结果。
"""

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的代码影响分析助手。请详细分析代码变更的影响范围和测试建议。"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self._call_openai_api(
                messages=messages,
                temperature=kwargs.get("temperature", 0.3),
            )

            impact_explanation = (
                response.get("choices", [{}])[0].get("message", {}).get("content", "")
            )

            return impact_explanation

        except Exception as e:
            logger.error(f"Failed to explain change impact: {e}")
            return f"影响分析失败: {str(e)}"

    def _call_openai_api(self, messages: list[dict], **kwargs: Any) -> dict[str, Any]:
        """调用 OpenAI API.

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            Dict[str, Any]: API 响应

        Raises:
            RuntimeError: API 调用失败
        """
        # 检查是否安装了 openai 库
        try:
            import openai  # type: ignore[import-not-found]
        except ImportError:
            logger.warning("OpenAI library not installed, using mock implementation")
            return {
                "choices": [{"message": {"content": "Mock response (OpenAI not installed)"}}],
                "usage": {"total_tokens": 100},
            }

        client = openai.OpenAI(  # type: ignore[attr-defined]
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=self._timeout,
        )

        # 重试机制
        for attempt in range(MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=kwargs.get("temperature", self._temperature),
                    max_tokens=kwargs.get("max_tokens", self._max_tokens),
                )

                return {
                    "choices": [{"message": {"content": response.choices[0].message.content}}],
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                }

            except openai.APITimeoutError:  # type: ignore[attr-defined]
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"OpenAI API timeout, retrying ({attempt + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise RuntimeError("OpenAI API request timed out") from None

            except openai.RateLimitError as e:  # type: ignore[attr-defined]
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"OpenAI API rate limit, retrying ({attempt + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY * (attempt + 1) * 2)
                else:
                    raise RuntimeError(f"OpenAI API rate limit: {e}") from e

            except openai.APIError as e:  # type: ignore[attr-defined]
                logger.error(f"OpenAI API error: {e}")
                raise RuntimeError(f"OpenAI API error: {e}") from e

        raise RuntimeError("Max retries exceeded") from None

    def _build_generation_context(
        self, request: TestGenerationRequest, project_path: Path
    ) -> dict[str, Any]:
        """构建生成上下文.

        Args:
            request: 测试生成请求
            project_path: 项目路径

        Returns:
            Dict[str, Any]: 上下文信息
        """
        context = {"project_path": str(project_path)}

        # 添加项目结构信息
        if project_path.exists():
            src_dir = project_path / "src" / "main" / "java"
            if src_dir.exists():
                context["src_structure"] = str(src_dir)

        return context

    def _build_test_generation_prompt(self, request: TestGenerationRequest, context: dict) -> str:
        """构建测试生成 prompt.

        Args:
            request: 测试生成请求
            context: 上下文信息

        Returns:
            str: prompt 内容
        """
        prompt = """
# 代码生成任务

## 目标类
"""
        for class_name in request.target_classes:
            prompt += f"- {class_name}\n"

        prompt += "\n## 相关代码\n"
        for class_name, code in request.code_snippets.items():
            prompt += f"\n### {class_name}\n```java\n{code}\n```\n"

        if context.get("dependencies"):
            prompt += "\n## 依赖信息\n"
            for dep in context["dependencies"]:
                prompt += f"- {dep}\n"

        if request.requirements:
            prompt += f"\n## 特殊要求\n{request.requirements}\n"

        prompt += """

## 代码规范

请为以上类生成完整的单元测试，每个测试类应该：
1. 使用 @Test 注解标记测试方法
2. 使用 @ExtendWith(MockitoExtension.class) 启用 Mockito
3. 为所有外部依赖创建 Mock 对象（使用 @Mock）
4. 使用 when().thenReturn() 设置 mock 行为
5. 测试正常流程和异常情况
6. 使用 assertThat 或 assertEquals 进行断言
7. 每个测试方法都有清晰的文档注释
8. 测试类和方法命名遵循约定

## 输出格式

请为每个目标类生成一个完整的测试类，使用 ```java``` 代码块包裹。
"""

        return prompt

    def _parse_test_generation_response(
        self, response: dict, target_classes: list[str]
    ) -> list[TestCase]:
        """解析生成的测试代码.

        Args:
            response: AI 响应数据
            target_classes: 目标类列表

        Returns:
            List[TestCase]: 测试用例列表
        """
        test_cases: list[TestCase] = []

        # 提取代码内容
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        # 解析所有 Java 代码块
        java_code_blocks = self._extract_all_java_code_blocks(content)

        # 为每个目标类创建 TestCase
        for i, target_class in enumerate(target_classes):
            test_code = java_code_blocks[i] if i < len(java_code_blocks) else ""

            # 解析测试方法名
            test_methods = self._extract_test_methods(test_code)

            test_case = TestCase(
                class_name=f"{target_class}Test",
                method_name="testGeneratedTest" if not test_methods else test_methods[0],
                test_type=TestType.UNIT,
                priority=TestPriority.HIGH,
                target_class=target_class,
                metadata={
                    "test_code": test_code,
                    "description": f"AI 生成的 {target_class} 测试用例",
                    "methods": test_methods,
                },
            )

            test_cases.append(test_case)

        return test_cases

    def _extract_java_code_from_response(self, response: dict) -> str:
        """从响应中提取 Java 代码.

        Args:
            response: AI 响应数据

        Returns:
            str: Java 代码
        """
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        code_blocks = self._extract_all_java_code_blocks(content)

        return code_blocks[0] if code_blocks else ""

    def _extract_all_java_code_blocks(self, content: str) -> list[str]:
        """提取所有 Java 代码块.

        Args:
            content: 响应内容

        Returns:
            List[str]: Java 代码块列表
        """
        # 匹配 ```java``` 代码块
        pattern = r"```java\s*\n?(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        return matches if matches else [content]

    def _extract_test_methods(self, test_code: str) -> list[str]:
        """提取测试方法名.

        Args:
            test_code: 测试代码

        Returns:
            List[str]: 测试方法名列表
        """
        # 匹配 @Test 注解的方法
        pattern = r"@Test\s*\n?\s*(?:public|private|protected)?\s*void\s+(\w+)\s*\("
        matches = re.findall(pattern, test_code)

        return matches

    def _extract_uncovered_segments(self, coverage_data: dict, project_path: Path) -> list[dict]:
        """提取未覆盖的代码段.

        Args:
            coverage_data: 覆盖率数据
            project_path: 项目路径

        Returns:
            List[dict]: 未覆盖代码段列表
        """
        segments = []

        for class_info in coverage_data.get("classes", []):
            class_name = class_info.get("name", "")
            line_coverage = class_info.get("line_coverage", 0)

            if line_coverage < 100:
                # 读取源代码
                source_file = self._find_source_file(class_name, project_path)

                if source_file and source_file.exists():
                    lines = source_file.read_text().split("\n")

                    # 提取未覆盖的行
                    uncovered_lines = [
                        i + 1  # 转换为 1-based
                        for i, covered in enumerate(class_info.get("lines", []))
                        if covered == 0
                    ]

                    if uncovered_lines:
                        first_line = min(uncovered_lines)
                        last_line = min(max(uncovered_lines), first_line + 20)

                        segment = {
                            "class_name": class_name,
                            "code": "\n".join(lines[first_line - 1 : last_line]),
                            "lines": uncovered_lines[: min(20, len(uncovered_lines))],
                            "branch": class_info.get("branch_coverage", 0),
                        }

                        segments.append(segment)

        return segments

    def _find_source_file(self, class_name: str, project_path: Path) -> Path | None:
        """查找源文件.

        Args:
            class_name: 类名
            project_path: 项目路径

        Returns:
            Path | None: 源文件路径
        """
        # 转换为文件路径
        path_parts = class_name.split(".")
        file_name = f"{path_parts[-1]}.java"
        dir_path = project_path.joinpath("src", "main", "java", *path_parts[:-1])

        java_file = dir_path / file_name
        if java_file.exists():
            return java_file

        return None

    def _estimate_confidence(self, response: dict) -> float:
        """估算置信度.

        Args:
            response: API 响应数据

        Returns:
            float: 置信度 (0-1)
        """
        usage = response.get("usage", {})
        total_tokens = usage.get("total_tokens", 0)

        # 基于token数量估算置信度
        if total_tokens < 100:
            return 0.3
        elif total_tokens < 500:
            return 0.5
        elif total_tokens < 1000:
            return 0.7
        else:
            return 0.9

    def _parse_code_findings(self, content: str) -> list[dict[str, Any]]:
        """解析代码分析结果.

        Args:
            content: AI 响应内容

        Returns:
            List[dict]: 分析结果列表
        """
        findings = []

        # 解析潜在问题
        issues_pattern = r"(?:潜在问题|问题|bug|issue)[:：:]\s*([^\n]+)"
        for match in re.finditer(issues_pattern, content, re.IGNORECASE):
            findings.append({"content": match.group(1).strip(), "severity": "INFO"})

        # 如果没有明确的问题，将整个内容作为finding
        if not findings:
            findings.append({"content": content, "severity": "INFO"})

        return findings

    def _parse_code_suggestions(self, content: str) -> list[str]:
        """解析代码改进建议.

        Args:
            content: AI 响应内容

        Returns:
            List[str]: 建议列表
        """
        suggestions = []

        # 解析改进建议
        suggestions_pattern = r"(?:改进建议|建议)[:：:]\s*([^\n]+)"
        for match in re.finditer(suggestions_pattern, content, re.IGNORECASE):
            suggestions.append(match.group(1).strip())

        # 如果没有明确的建议，添加通用建议
        if not suggestions:
            suggestions = ["请根据代码质量评估进行改进"]

        return suggestions

    def _extract_risk_level(self, content: str) -> str:
        """提取风险级别.

        Args:
            content: AI 响应内容

        Returns:
            str: 风险级别 (HIGH/MEDIUM/LOW)
        """
        content_upper = content.upper()

        # 使用正则表达式匹配，确保是独立的单词
        if re.search(r"\bHIGH\b", content_upper):
            return "HIGH"
        if re.search(r"\bLOW\b", content_upper):
            return "LOW"

        return "MEDIUM"
