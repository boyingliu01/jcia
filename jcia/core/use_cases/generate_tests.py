"""生成测试用例用例.

负责协调测试生成服务，为指定类或未覆盖代码生成测试用例。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jcia.core.entities.test_case import TestCase
    from jcia.core.interfaces.ai_service import (
        AITestGenerator,
    )


@dataclass
class GenerateTestsRequest:
    """生成测试请求.

    Attributes:
        project_path: 项目路径
        target_classes: 目标类列表（类全限定名）
        coverage_data: 覆盖率数据（用于为未覆盖代码生成测试）
        output_dir: 输出目录（可选）
        min_confidence: 最低置信度阈值
        priority: 生成测试的优先级
    """

    project_path: Path
    target_classes: list[str] = field(default_factory=list)
    coverage_data: dict[str, Any] | None = None
    output_dir: Path | None = None
    min_confidence: float = 0.5
    priority: str = "medium"


@dataclass
class GenerateTestsResponse:
    """生成测试响应.

    Attributes:
        test_cases: 生成的测试用例列表
        generated_count: 生成数量
        filtered_count: 过滤掉的数量
        confidence: 整体置信度
        explanations: 生成说明
        metadata: 额外元数据
    """

    test_cases: list["TestCase"]
    generated_count: int = 0
    filtered_count: int = 0
    confidence: float = 0.0
    explanations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class GenerateTestsUseCase:
    """生成测试用例用例.

    协调测试生成服务，为指定类或未覆盖代码生成测试用例。

    流程：
        1. 验证请求参数
        2. 根据请求类型生成测试
           - 基于目标类生成
           - 基于覆盖率数据生成
        3. 按置信度过滤
        4. 按优先级排序
        5. 生成响应
    """

    def __init__(self, ai_generator: "AITestGenerator") -> None:
        """初始化用例.

        Args:
            ai_generator: AI测试生成器
        """
        # 导入TestGeneratorService避免循环依赖
        from jcia.core.services.test_generator_service import TestGeneratorService

        self._service = TestGeneratorService(ai_generator=ai_generator)

    def execute(self, request: GenerateTestsRequest) -> GenerateTestsResponse:
        """执行生成测试用例用例.

        Args:
            request: 生成测试请求

        Returns:
            GenerateTestsResponse: 生成响应

        Raises:
            ValueError: 请求参数无效
            Exception: 生成过程中发生错误
        """
        # 验证请求
        self._validate_request(request)

        # 根据请求类型生成测试
        if request.target_classes:
            response = self._generate_for_classes(request)
        elif request.coverage_data:
            response = self._generate_for_coverage(request)
        else:
            msg = "必须提供target_classes或coverage_data"
            raise ValueError(msg)

        # 后处理
        response.test_cases = self._prioritize_tests(response.test_cases)
        response.generated_count = len(response.test_cases)

        return response

    def _validate_request(self, request: GenerateTestsRequest) -> None:
        """验证请求参数.

        Args:
            request: 生成测试请求

        Raises:
            ValueError: 请求参数无效
        """
        if not request.project_path.exists():
            msg = f"项目路径不存在: {request.project_path}"
            raise ValueError(msg)

        if not request.target_classes and not request.coverage_data:
            msg = "必须提供target_classes或coverage_data之一"
            raise ValueError(msg)

        if request.min_confidence < 0 or request.min_confidence > 1:
            msg = "min_confidence必须在0和1之间"
            raise ValueError(msg)

    def _generate_for_classes(self, request: GenerateTestsRequest) -> GenerateTestsResponse:
        """为指定类生成测试.

        Args:
            request: 生成测试请求

        Returns:
            GenerateTestsResponse: 生成响应
        """
        # 导入请求类型避免循环依赖
        from jcia.core.interfaces.ai_service import TestGenerationRequest

        # 创建生成请求
        gen_request = TestGenerationRequest(
            target_classes=request.target_classes,
            code_snippets={},  # 由服务填充
            context={"output_dir": str(request.output_dir) if request.output_dir else None},
            requirements=None,
        )

        # 调用服务生成测试
        gen_response = self._service.generate_tests(
            request=gen_request,
            project_path=request.project_path,
        )

        # 过滤低置信度测试
        filtered_response = self._service.filter_by_confidence(
            gen_response, min_confidence=request.min_confidence
        )

        # 转换为响应
        return GenerateTestsResponse(
            test_cases=filtered_response.test_cases,
            confidence=filtered_response.confidence,
            explanations=filtered_response.explanations,
        )

    def _generate_for_coverage(self, request: GenerateTestsRequest) -> GenerateTestsResponse:
        """为未覆盖代码生成测试.

        Args:
            request: 生成测试请求

        Returns:
            GenerateTestsResponse: 生成响应
        """
        # 调用服务为未覆盖代码生成测试
        gen_response = self._service.generate_for_uncovered(
            coverage_data=request.coverage_data or {},
            project_path=request.project_path,
        )

        # 过滤低置信度测试
        filtered_response = self._service.filter_by_confidence(
            gen_response, min_confidence=request.min_confidence
        )

        # 转换为响应
        return GenerateTestsResponse(
            test_cases=filtered_response.test_cases,
            confidence=filtered_response.confidence,
            explanations=filtered_response.explanations,
        )

    def _prioritize_tests(self, test_cases: list["TestCase"]) -> list["TestCase"]:
        """按优先级排序测试用例.

        Args:
            test_cases: 测试用例列表

        Returns:
            List[TestCase]: 排序后的测试用例
        """
        return self._service.prioritize_tests(test_cases)
