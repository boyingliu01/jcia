"""AI 服务抽象接口定义.

定义与 AI/LLM 服务交互的抽象接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jcia.core.entities.test_case import TestCase


class AIProvider(Enum):
    """AI 服务提供商枚举."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    VOLCENGINE = "volcengine"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class TestGenerationRequest:
    """测试生成请求.

    Attributes:
        target_classes: 目标类列表
        code_snippets: 相关代码片段
        context: 额外上下文信息
        requirements: 生成要求
    """

    __test__ = False  # 避免被 pytest 收集

    target_classes: list[str]

    code_snippets: dict[str, str]
    context: dict[str, Any]
    requirements: str | None = None


@dataclass
class TestGenerationResponse:
    """测试生成响应.

    Attributes:
        test_cases: 生成的测试用例
        explanations: 测试说明
        confidence: 置信度 (0-1)
        tokens_used: 使用的 token 数量
    """

    test_cases: list["TestCase"]
    explanations: list[str]
    confidence: float = 0.0
    tokens_used: int = 0


@dataclass
class CodeAnalysisRequest:
    """代码分析请求.

    Attributes:
        code: 要分析的代码
        analysis_type: 分析类型
        context: 上下文信息
    """

    code: str
    analysis_type: str
    context: dict[str, Any] | None = None


@dataclass
class CodeAnalysisResponse:
    """代码分析响应.

    Attributes:
        findings: 分析结果
        suggestions: 改进建议
        risk_level: 风险级别
    """

    findings: list[dict[str, Any]]
    suggestions: list[str]
    risk_level: str = "LOW"


class AITestGenerator(ABC):
    """AI 测试生成器抽象接口.

    使用 AI/LLM 服务生成测试用例。
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def refine_test(
        self,
        test_case: "TestCase",
        feedback: str,
        project_path: Path,
        **kwargs: Any,
    ) -> "TestCase":
        """根据反馈优化测试用例.

        Args:
            test_case: 原始测试用例
            feedback: 反馈信息
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            TestCase: 优化后的测试用例
        """
        pass

    @property
    @abstractmethod
    def provider(self) -> AIProvider:
        """返回 AI 服务提供商."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """返回使用的模型名称."""
        pass


class AIAnalyzer(ABC):
    """AI 代码分析器抽象接口.

    使用 AI/LLM 服务分析代码。
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @property
    @abstractmethod
    def provider(self) -> AIProvider:
        """返回 AI 服务提供商."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """返回使用的模型名称."""
        pass
