"""测试运行领域实体.

表示基线测试或回归测试的一次执行。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TestStatus(Enum):
    """测试状态枚举."""

    __test__ = False
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    RUNNING = "running"
    PENDING = "pending"


class RunType(Enum):
    """运行类型枚举."""

    BASELINE = "baseline"  # 基线测试
    REGRESSION = "regression"  # 回归测试


class RunStatus(Enum):
    """运行状态枚举."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DiffType(Enum):
    """测试差异类型枚举."""

    NEW_PASS = "NEW_PASS"  # noqa: S105  # nosec B105
    NEW_FAIL = "NEW_FAIL"
    STABLE_PASS = "STABLE_PASS"  # noqa: S105  # nosec B105
    STABLE_FAIL = "STABLE_FAIL"

    REMOVED = "REMOVED"


@dataclass
class CoverageData:
    """覆盖率数据.

    Attributes:
        line_coverage: 行覆盖率（百分比）
        branch_coverage: 分支覆盖率
        method_coverage: 方法覆盖率
        class_coverage: 类覆盖率
        covered_lines: 已覆盖行数
        total_lines: 总行数
        details: 详细覆盖率数据
    """

    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    method_coverage: float = 0.0
    class_coverage: float = 0.0
    covered_lines: int = 0
    total_lines: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def coverage_ratio(self) -> float:
        """返回覆盖率比例（0-1）."""
        if self.line_coverage <= 0:
            return 0.0
        if self.line_coverage >= 100.0:
            return 1.0
        return self.line_coverage / 100.0


@dataclass
class TestResult:
    """单个测试结果.

    Attributes:
        id: 结果ID
        test_run_id: 所属测试运行ID
        test_class: 测试类名
        test_method: 测试方法名
        status: 测试状态
        duration_ms: 执行时长（毫秒）
        error_message: 错误信息
        stack_trace: 堆栈跟踪
        coverage_data: 覆盖率数据
        timestamp: 执行时间
    """

    __test__ = False  # 不要被pytest收集为测试类

    id: int | None = None
    test_run_id: int | None = None
    test_class: str = ""
    test_method: str = ""
    status: TestStatus = TestStatus.PENDING
    duration_ms: int = 0
    error_message: str | None = None
    stack_trace: str | None = None
    coverage_data: CoverageData | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def full_name(self) -> str:
        """返回测试全限定名."""
        return f"{self.test_class}#{self.test_method}"

    @property
    def passed(self) -> bool:
        """是否通过."""
        return self.status == TestStatus.PASSED

    @property
    def failed(self) -> bool:
        """是否失败."""
        return self.status == TestStatus.FAILED

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "test_run_id": self.test_run_id,
            "full_name": self.full_name,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class TestRun:
    """测试运行.

    表示一次完整的测试执行（基线或回归）。

    Attributes:
        id: 运行ID
        run_type: 运行类型
        commit_hash: 关联的提交哈希
        commit_message: 提交消息
        branch_name: 分支名
        timestamp: 运行时间
        status: 运行状态
        total_tests: 总测试数
        passed_tests: 通过数
        failed_tests: 失败数
        skipped_tests: 跳过数
        error_tests: 错误数
        total_duration_ms: 总执行时长
        coverage: 覆盖率数据
        test_results: 测试结果列表
        metadata: 额外元数据
    """

    __test__ = False  # 不要被pytest收集为测试类

    id: int | None = None
    run_type: RunType = RunType.REGRESSION
    commit_hash: str = ""
    commit_message: str | None = None
    branch_name: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    status: RunStatus = RunStatus.PENDING
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    total_duration_ms: int = 0
    coverage: CoverageData | None = None
    test_results: list[TestResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def short_commit_hash(self) -> str:
        """返回短哈希."""
        return self.commit_hash[:7] if len(self.commit_hash) >= 7 else self.commit_hash

    @property
    def success_rate(self) -> float:
        """成功率."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests

    @property
    def is_baseline(self) -> bool:
        """是否是基线测试."""
        return self.run_type == RunType.BASELINE

    @property
    def is_regression(self) -> bool:
        """是否是回归测试."""
        return self.run_type == RunType.REGRESSION

    @property
    def has_failures(self) -> bool:
        """是否有失败."""
        return self.failed_tests > 0 or self.error_tests > 0

    def add_result(self, result: TestResult) -> None:
        """添加测试结果.

        Args:
            result: 测试结果
        """
        result.test_run_id = self.id
        self.test_results.append(result)
        self._update_counts()

    def add_results(self, results: list[TestResult]) -> None:
        """批量添加测试结果.

        Args:
            results: 测试结果列表
        """
        for result in results:
            result.test_run_id = self.id
            self.test_results.append(result)
        self._update_counts()

    def _update_counts(self) -> None:
        """更新计数."""
        self.total_tests = len(self.test_results)
        self.passed_tests = sum(1 for r in self.test_results if r.passed)
        self.failed_tests = sum(1 for r in self.test_results if r.failed)
        self.skipped_tests = sum(1 for r in self.test_results if r.status == TestStatus.SKIPPED)
        self.error_tests = sum(1 for r in self.test_results if r.status == TestStatus.ERROR)

    def get_failed_results(self) -> list[TestResult]:
        """获取失败的测试结果."""
        return [r for r in self.test_results if r.failed]

    def get_result_by_name(self, test_name: str) -> TestResult | None:
        """根据名称获取结果.

        Args:
            test_name: 测试全限定名（类名#方法名）

        Returns:
            Optional[TestResult]: 测试结果
        """
        for result in self.test_results:
            if result.full_name == test_name:
                return result
        return None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "run_type": self.run_type.value,
            "commit_hash": self.commit_hash,
            "short_commit_hash": self.short_commit_hash,
            "commit_message": self.commit_message,
            "branch_name": self.branch_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status.value,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "error_tests": self.error_tests,
            "success_rate": self.success_rate,
            "total_duration_ms": self.total_duration_ms,
            "coverage": self.coverage.line_coverage if self.coverage else 0.0,
        }


@dataclass
class TestDiff:
    """测试差异.

    表示基线测试和回归测试之间的差异。

    Attributes:
        id: 差异ID
        baseline_run_id: 基线运行ID
        regression_run_id: 回归运行ID
        test_class: 测试类名
        test_method: 测试方法名
        baseline_status: 基线状态
        regression_status: 回归状态
        diff_type: 差异类型
        analysis_result: 分析结果
        analysis_reason: 分析原因
    """

    __test__ = False  # 不要被pytest收集为测试类

    id: int | None = None
    baseline_run_id: int = 0
    regression_run_id: int = 0
    test_class: str = ""
    test_method: str = ""
    baseline_status: TestStatus | None = None
    regression_status: TestStatus | None = None
    diff_type: DiffType = DiffType.STABLE_PASS
    analysis_result: str = "PENDING"  # EXPECTED, UNEXPECTED, NEED_REVIEW
    analysis_reason: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None

    @property
    def full_name(self) -> str:
        """返回测试全限定名."""
        return f"{self.test_class}#{self.test_method}"

    @property
    def is_new_pass(self) -> bool:
        """是否是新增通过."""
        return self.diff_type == DiffType.NEW_PASS

    @property
    def is_new_fail(self) -> bool:
        """是否是新增失败."""
        return self.diff_type == DiffType.NEW_FAIL

    @property
    def is_regression_issue(self) -> bool:
        """是否是回归问题（基线通过，回归失败）."""
        return self.baseline_status == TestStatus.PASSED and self.regression_status in (
            TestStatus.FAILED,
            TestStatus.ERROR,
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "baseline_status": self.baseline_status.value if self.baseline_status else None,
            "regression_status": self.regression_status.value if self.regression_status else None,
            "diff_type": self.diff_type.value,
            "is_regression_issue": self.is_regression_issue,
            "analysis_result": self.analysis_result,
            "analysis_reason": self.analysis_reason,
        }


@dataclass
class TestComparison:
    """测试对比结果.

    包含基线和回归测试的完整对比。
    """

    __test__ = False  # 不要被pytest收集为测试类

    baseline_run: TestRun | None = None
    regression_run: TestRun | None = None
    diffs: list[TestDiff] = field(default_factory=list)

    @property
    def new_passes(self) -> list[TestDiff]:
        """新增通过的测试."""
        return [d for d in self.diffs if d.is_new_pass]

    @property
    def new_failures(self) -> list[TestDiff]:
        """新增失败的测试."""
        return [d for d in self.diffs if d.is_new_fail]

    @property
    def regression_issues(self) -> list[TestDiff]:
        """回归问题列表."""
        return [d for d in self.diffs if d.is_regression_issue]

    @property
    def has_regression_issues(self) -> bool:
        """是否有回归问题."""
        return len(self.regression_issues) > 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "baseline": self.baseline_run.to_dict() if self.baseline_run else None,
            "regression": self.regression_run.to_dict() if self.regression_run else None,
            "diff_summary": {
                "total_diffs": len(self.diffs),
                "new_passes": len(self.new_passes),
                "new_failures": len(self.new_failures),
                "regression_issues": len(self.regression_issues),
            },
            "diffs": [d.to_dict() for d in self.diffs],
        }


__all__ = [
    "CoverageData",
    "RunStatus",
    "RunType",
    "TestComparison",
    "TestDiff",
    "TestResult",
    "TestRun",
    "TestStatus",
]
