"""测试生成领域服务.

基于AI/LLM服务为未覆盖代码生成测试用例。
"""

from pathlib import Path
from typing import Any

from jcia.core.entities.test_case import TestCase, TestPriority
from jcia.core.interfaces.ai_service import (
    AITestGenerator,
    TestGenerationRequest,
    TestGenerationResponse,
)


class TestGeneratorService:
    """测试生成服务.

    协调AI服务生成和优化测试用例。
    """

    def __init__(self, ai_generator: AITestGenerator) -> None:
        """初始化服务.

        Args:
            ai_generator: AI测试生成器
        """
        self._ai_generator = ai_generator

    def generate_tests(
        self, request: TestGenerationRequest, project_path: Path, **kwargs: Any
    ) -> TestGenerationResponse:
        """为指定类生成测试用例.

        Args:
            request: 测试生成请求
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            TestGenerationResponse: 生成响应
        """
        return self._ai_generator.generate_tests(
            request=request, project_path=project_path, **kwargs
        )

    def generate_for_uncovered(
        self, coverage_data: dict[str, Any], project_path: Path, **kwargs: Any
    ) -> TestGenerationResponse:
        """为未覆盖代码生成测试.

        Args:
            coverage_data: 覆盖率数据
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            TestGenerationResponse: 生成响应
        """
        return self._ai_generator.generate_for_uncovered(
            coverage_data=coverage_data, project_path=project_path, **kwargs
        )

    def refine_test_case(
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
        return self._ai_generator.refine_test(
            test_case=test_case,
            feedback=feedback,
            project_path=project_path,
            **kwargs,
        )

    def merge_test_cases(self, test_lists: list[list[TestCase]]) -> list[TestCase]:
        """合并多个测试用例列表，去重.

        Args:
            test_lists: 测试用例列表的列表

        Returns:
            List[TestCase]: 合并后的测试用例列表
        """
        seen = set()
        result: list[TestCase] = []

        for test_list in test_lists:
            for test_case in test_list:
                test_key = test_case.full_name
                if test_key not in seen:
                    seen.add(test_key)
                    result.append(test_case)

        return result

    def prioritize_tests(self, test_cases: list[TestCase]) -> list[TestCase]:
        """按优先级排序测试用例.

        Args:
            test_cases: 测试用例列表

        Returns:
            List[TestCase]: 排序后的测试用例
        """
        priority_order = [
            TestPriority.CRITICAL,
            TestPriority.HIGH,
            TestPriority.MEDIUM,
            TestPriority.LOW,
        ]

        def get_priority_index(test: TestCase) -> int:
            try:
                return priority_order.index(test.priority)
            except ValueError:
                return len(priority_order)  # Unknown priority goes last

        return sorted(test_cases, key=get_priority_index)

    def filter_by_confidence(
        self, response: TestGenerationResponse, min_confidence: float = 0.5
    ) -> TestGenerationResponse:
        """按置信度过滤生成的测试.

        Args:
            response: 生成响应
            min_confidence: 最低置信度

        Returns:
            TestGenerationResponse: 过滤后的响应
        """
        if response.confidence < min_confidence:
            return TestGenerationResponse(
                test_cases=[],
                explanations=["Confidence too low"],
                confidence=response.confidence,
                tokens_used=response.tokens_used,
            )

        return response

    def analyze_testability(self, code: str) -> dict[str, Any]:
        """分析代码的可测试性.

        Args:
            code: 代码片段

        Returns:
            Dict[str, Any]: 可测试性分析结果
        """
        # 简单分析：识别公共方法和类
        testable_methods = []
        suggestions = []

        lines = code.split("\n")
        in_class = False
        class_name = ""

        for line in lines:
            # 检测类定义
            if "class " in line and "{" in line:
                parts = line.split("class ")[1].split("{")[0].strip()
                class_name = parts.split()[0]
                in_class = True

            # 检测公共方法
            if (
                in_class
                and "public" in line
                and ("(" in line or "def " in line)
                and "test" not in line.lower()
            ):
                if "(" in line:
                    method_part = line.split("(")[0].strip()
                else:
                    method_part = line.split("def ")[1].split("(")[0].strip()
                testable_methods.append(f"{class_name}.{method_part}")

        # 生成建议
        if not testable_methods:
            suggestions.append("No public methods found to test")
        else:
            suggestions.append(f"Found {len(testable_methods)} testable methods")

        return {
            "testable_methods": testable_methods,
            "suggestions": suggestions,
        }

    def get_coverage_gap_analysis(
        self,
        baseline_coverage: dict[str, Any] | None,
        target_coverage: float = 0.8,
    ) -> dict[str, Any]:
        """分析覆盖率差距.

        Args:
            baseline_coverage: 基线覆盖率数据
            target_coverage: 目标覆盖率

        Returns:
            Dict[str, Any]: 覆盖率差距分析
        """
        if baseline_coverage is None:
            return {"gap": target_coverage, "suggestion": "Start testing from critical classes"}

        current_coverage = baseline_coverage.get("line_coverage", 0.0)
        gap = target_coverage - current_coverage

        suggestion = ""
        if gap > 0.3:
            suggestion = "Significant coverage gap. Focus on high-impact classes first."
        elif gap > 0.1:
            suggestion = "Moderate coverage gap. Add tests for edge cases."
        else:
            suggestion = "Coverage near target. Add tests for boundary conditions."

        return {
            "current": current_coverage,
            "target": target_coverage,
            "gap": max(0, gap),
            "suggestion": suggestion,
        }
