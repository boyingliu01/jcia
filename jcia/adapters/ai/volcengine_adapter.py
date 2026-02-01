"""火山引擎 LLM 适配器实现."""

from pathlib import Path
from typing import Any

import requests

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

# 常量定义
DEFAULT_MODEL = "doubao-pro-32k"
DEFAULT_REGION = "cn-beijing"
DEFAULT_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DEFAULT_TEMPERATURE = 0.7
REQUEST_TIMEOUT = 30  # 秒


class VolcengineAdapter(AITestGenerator, AIAnalyzer):
    """火山引擎 LLM 服务适配器.

    使用火山引擎 API 进行测试生成和代码分析。
    """

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        app_id: str,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        region: str = DEFAULT_REGION,
        **kwargs: Any,
    ) -> None:
        """初始化适配器.

        Args:
            access_key: 访问密钥
            secret_key: 秘钥
            app_id: 应用ID
            model: 模型名称（默认 doubao-pro-32k）
            temperature: 温度参数（0-1）
            region: 区域（默认 cn-beijing）
            **kwargs: 额外配置参数
        """
        self._access_key = access_key
        self._secret_key = secret_key
        self._app_id = app_id
        self._model = model
        self._temperature = temperature
        self._region = region
        self._endpoint = DEFAULT_ENDPOINT

    @property
    def provider(self) -> AIProvider:
        """返回 AI 服务提供商."""
        return AIProvider.OPENAI  # 使用OPENAI标识符（兼容接口）

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
        # 构建 prompt
        prompt = self._build_test_generation_prompt(request)

        # 调用火山引擎 API
        response_data = self._call_api(
            messages=[
                {"role": "system", "content": "你是一个专业的测试代码生成助手。"},
                {"role": "user", "content": prompt},
            ],
            **kwargs,
        )

        # 解析响应
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = response_data.get("usage", {})
        test_cases = self._parse_generated_tests(content, request.target_classes)
        explanations = [f"为 {cls} 生成测试用例" for cls in request.target_classes]

        return TestGenerationResponse(
            test_cases=test_cases,
            explanations=explanations,
            confidence=self._estimate_confidence(usage),
            tokens_used=usage.get("total_tokens", 0),
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
        # 提取未覆盖的类/方法
        uncovered_items = self._extract_uncovered_items(coverage_data)

        # 构建请求
        request = TestGenerationRequest(
            target_classes=uncovered_items,
            code_snippets={},
            context={"project_path": str(project_path)},
            requirements="为以下未覆盖代码生成测试用例，以提高覆盖率。",
        )

        # 调用通用生成方法
        return self.generate_tests(request, project_path, **kwargs)

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
        # 构建优化 prompt
        original_code = test_case.metadata.get("test_code", "")
        prompt = f"""
        原始测试用例:
        ```java
        {original_code}
        ```

        反馈意见:
        {feedback}

        请根据反馈意见优化测试用例，使其更加健壮和全面。
        """

        # 调用火山引擎 API
        response_data = self._call_api(
            messages=[
                {"role": "system", "content": "你是一个专业的测试代码优化助手。"},
                {"role": "user", "content": prompt},
            ],
            **kwargs,
        )

        # 更新测试用例
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        refined_code = content if content else original_code
        test_case.metadata["test_code"] = refined_code

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
        # 构建分析 prompt
        prompt = f"""
        请分析以下代码:

        ```java
        {request.code}
        ```

        分析类型: {request.analysis_type}

        提供以下信息:
        1. 代码质量评估
        2. 潜在问题
        3. 改进建议
        4. 风险级别 (HIGH/MEDIUM/LOW)
        """

        # 调用火山引擎 API
        response_data = self._call_api(
            messages=[
                {"role": "system", "content": "你是一个专业的代码分析助手。"},
                {"role": "user", "content": prompt},
            ],
            **kwargs,
        )

        # 解析响应
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        findings = self._parse_code_findings(content)
        suggestions = self._parse_code_suggestions(content)
        risk_level = self._extract_risk_level(content)

        return CodeAnalysisResponse(
            findings=findings,
            suggestions=suggestions,
            risk_level=risk_level,
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
        # 构建分析 prompt
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
        """

        # 调用火山引擎 API
        response_data = self._call_api(
            messages=[
                {"role": "system", "content": "你是一个专业的代码影响分析助手。"},
                {"role": "user", "content": prompt},
            ],
            **kwargs,
        )

        return response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _call_api(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """调用火山引擎 API.

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            Dict[str, Any]: API 响应数据
        """
        payload = self._build_payload(messages, **kwargs)
        headers = self._build_headers()

        try:
            response = requests.post(
                self._endpoint,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return {"choices": [{"message": {"content": ""}}], "usage": {}}

    def _build_payload(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """构建请求负载，包含模型、温度和 app_id 信息."""
        return {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "app_id": self._app_id,
            **kwargs,
        }

    def _build_headers(self) -> dict[str, str]:
        """构建鉴权请求头."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"VolcengineAK {self._access_key}:{self._secret_key}",
            "X-Volc-App-Id": self._app_id,
            "X-Volc-Region": self._region,
        }

    def _build_test_generation_prompt(self, request: TestGenerationRequest) -> str:
        """构建测试生成 prompt.

        Args:
            request: 测试生成请求

        Returns:
            str: prompt 内容
        """
        prompt = f"""
        请为以下 Java 类生成单元测试用例:

        目标类:
        {", ".join(request.target_classes)}

        代码片段:
        """
        for class_name, code in request.code_snippets.items():
            prompt += f"\n{class_name}:\n```java\n{code}\n```\n"

        if request.requirements:
            prompt += f"\n测试要求:\n{request.requirements}\n"

        prompt += """
        请生成完整的测试用例，包括:
        - 正常情况测试
        - 边界条件测试
        - 异常情况测试

        测试代码应使用 JUnit 5 框架。
        """
        return prompt

    def _parse_generated_tests(
        self,
        content: str,
        target_classes: list[str],
    ) -> list[TestCase]:
        """解析生成的测试代码.

        Args:
            content: AI 响应内容
            target_classes: 目标类列表

        Returns:
            List[TestCase]: 测试用例列表
        """
        test_cases: list[TestCase] = []

        for target_class in target_classes:
            test_case = TestCase(
                class_name=f"{target_class}Test",
                method_name="testGeneratedTest",
                test_type=TestType.UNIT,
                priority=TestPriority.MEDIUM,
                target_class=target_class,
                metadata={
                    "test_code": content,
                    "description": f"AI 生成的 {target_class} 测试用例",
                },
            )

            test_cases.append(test_case)

        return test_cases

    def _extract_uncovered_items(
        self,
        coverage_data: dict[str, Any],
    ) -> list[str]:
        """提取未覆盖的类/方法.

        Args:
            coverage_data: 覆盖率数据

        Returns:
            List[str]: 未覆盖项列表
        """
        uncovered_items: list[str] = []
        if "uncovered_classes" in coverage_data:
            uncovered_items.extend(coverage_data["uncovered_classes"])
        if "uncovered_methods" in coverage_data:
            uncovered_items.extend(coverage_data["uncovered_methods"])
        return uncovered_items

    def _estimate_confidence(self, usage: dict[str, Any]) -> float:
        """估算置信度.

        Args:
            usage: token 使用数据

        Returns:
            float: 置信度 (0-1)
        """
        total_tokens = usage.get("total_tokens", 0)
        # 假设合理的 token 数量对应较高的置信度（阈值1000）
        confidence_threshold = 1000
        return min(total_tokens / confidence_threshold, 1.0)

    def _parse_code_findings(self, content: str) -> list[dict[str, Any]]:
        """解析代码分析结果.

        Args:
            content: AI 响应内容

        Returns:
            List[Dict[str, Any]]: 分析结果列表
        """
        return [{"content": content, "severity": "INFO"}]

    def _parse_code_suggestions(self, content: str) -> list[str]:
        """解析代码改进建议.

        Args:
            content: AI 响应内容

        Returns:
            List[str]: 建议列表
        """
        return [content]

    def _extract_risk_level(self, content: str) -> str:
        """提取风险级别.

        Args:
            content: AI 响应内容

        Returns:
            str: 风险级别 (HIGH/MEDIUM/LOW)
        """
        risk_keywords = {"HIGH": "HIGH", "LOW": "LOW"}
        content_upper = content.upper()

        for keyword, level in risk_keywords.items():
            if keyword in content_upper:
                return level

        return "MEDIUM"
