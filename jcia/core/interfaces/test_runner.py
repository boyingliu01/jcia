"""测试运行器抽象接口.

定义测试选择、生成和执行的抽象接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jcia.core.entities.test_case import TestCase
    from jcia.core.entities.test_run import TestStatus


class TestSelectionStrategy(Enum):
    """测试选择策略枚举."""

    __test__ = False  # 避免被 pytest 收集

    ALL = "all"  # 运行所有测试
    STARTS = "starts"  # 使用STARTS选择
    IMPACT_BASED = "impact"  # 基于影响范围选择
    HYBRID = "hybrid"  # 混合策略


@dataclass
class TestExecutionResult:
    """测试执行结果.
    测试运行器返回的详细结果。
    """

    __test__ = False
    test_class: str
    test_method: str
    status: "TestStatus"
    duration_ms: int = 0
    error_message: str | None = None
    stack_trace: str | None = None
    coverage_percent: float = 0.0


@dataclass
class TestSuiteResult:
    """测试套件执行结果."""

    __test__ = False  # 避免被 pytest 收集

    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    total_duration_ms: int = 0
    coverage_percent: float = 0.0
    test_results: list[TestExecutionResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化后处理."""
        if self.test_results is None:
            self.test_results = []

    @property
    def success_rate(self) -> float:
        """计算成功率."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests


class TestSelector(ABC):
    """测试选择器抽象接口."""

    @abstractmethod
    def select_tests(
        self, changed_methods: list[str], project_path: Path, **kwargs: Any
    ) -> list["TestCase"]:
        """选择需要执行的测试用例.

        Args:
            changed_methods: 变更的方法列表
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            List[TestCase]: 选中的测试用例列表
        """
        pass

    @abstractmethod
    def get_selection_strategy(self) -> TestSelectionStrategy:
        """获取选择策略."""
        pass


class TestGenerator(ABC):
    """测试生成器抽象接口."""

    @abstractmethod
    def generate_tests(
        self,
        target_classes: list[str],
        project_path: Path,
        output_dir: Path | None = None,
        **kwargs: Any,
    ) -> list["TestCase"]:
        """为指定类生成测试用例.

        Args:
            target_classes: 目标类列表
            project_path: 项目路径
            output_dir: 输出目录
            **kwargs: 额外参数

        Returns:
            List[TestCase]: 生成的测试用例列表
        """
        pass

    @abstractmethod
    def generate_for_uncovered(
        self, coverage_report: dict[str, Any], project_path: Path, **kwargs: Any
    ) -> list["TestCase"]:
        """为未覆盖代码生成测试.

        Args:
            coverage_report: 覆盖率报告
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            List[TestCase]: 生成的测试用例列表
        """
        pass


class TestExecutor(ABC):
    """测试执行器抽象接口."""

    @abstractmethod
    def execute_tests(
        self,
        test_cases: list["TestCase"] | None = None,
        project_path: Path | None = None,
        **kwargs: Any,
    ) -> TestSuiteResult:
        """执行测试.

        Args:
            test_cases: 要执行的测试用例（None则执行所有）
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            TestSuiteResult: 测试结果
        """
        pass

    @abstractmethod
    def execute_with_coverage(
        self,
        test_cases: list["TestCase"] | None = None,
        project_path: Path | None = None,
        **kwargs: Any,
    ) -> TestSuiteResult:
        """执行测试并收集覆盖率.

        Args:
            test_cases: 要执行的测试用例
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            TestSuiteResult: 包含覆盖率的测试结果
        """
        pass

    @abstractmethod
    def get_coverage_report(self, project_path: Path, report_format: str = "xml") -> dict[str, Any]:
        """获取覆盖率报告.

        Args:
            project_path: 项目路径
            report_format: 报告格式（xml/html/csv）

        Returns:
            Dict[str, Any]: 覆盖率数据
        """
        pass
