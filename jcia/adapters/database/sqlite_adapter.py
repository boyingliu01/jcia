"""SQLite 数据库适配器（Adapters 层封装）。"""

from typing import TYPE_CHECKING

from jcia.core.entities.test_run import RunStatus, RunType, TestDiff, TestResult, TestRun
from jcia.infrastructure.database.sqlite_adapter import SQLiteAdapter
from jcia.infrastructure.database.sqlite_repository import (
    SQLiteTestDiffRepository,
    SQLiteTestResultRepository,
    SQLiteTestRunRepository,
)

if TYPE_CHECKING:
    from jcia.core.interfaces.repository import (
        TestDiffRepository,
        TestResultRepository,
        TestRunRepository,
    )


class SQLiteDatabaseAdapter:
    """适配 SQLite 数据库，提供仓储实例的便捷封装."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._adapter = SQLiteAdapter(db_path)
        self._adapter.connect()
        self.test_run_repo: TestRunRepository = SQLiteTestRunRepository(self._adapter)
        self.test_result_repo: TestResultRepository = SQLiteTestResultRepository(self._adapter)
        self.test_diff_repo: TestDiffRepository = SQLiteTestDiffRepository(self._adapter)

    @property
    def is_connected(self) -> bool:
        """是否已连接数据库."""
        return self._adapter.is_connected()

    def close(self) -> None:
        """关闭数据库连接."""
        self._adapter.disconnect()

    # 便捷创建实体的辅助方法（供上层用例/测试快速构造）
    def create_test_run(
        self,
        commit_hash: str,
        run_type: RunType = RunType.REGRESSION,
        status: RunStatus = RunStatus.PENDING,
    ) -> TestRun:
        """创建 TestRun 实例（未持久化）。"""
        return TestRun(commit_hash=commit_hash, run_type=run_type, status=status)

    def create_test_result(
        self,
        run_id: int,
        test_class: str,
        test_method: str,
        status: RunStatus | None = None,
    ) -> TestResult:
        """创建 TestResult 实例（未持久化）。"""
        test_status = status if status is not None else RunStatus.PENDING
        return TestResult(
            test_run_id=run_id,
            test_class=test_class,
            test_method=test_method,
            status=test_status,  # type: ignore[arg-type]
        )

    def create_test_diff(
        self,
        baseline_run_id: int,
        regression_run_id: int,
        test_class: str,
        test_method: str,
        baseline_status: RunStatus | None,
        regression_status: RunStatus | None,
        diff_type: str,
    ) -> TestDiff:
        """创建 TestDiff 实例（未持久化）。"""
        return TestDiff(
            baseline_run_id=baseline_run_id,
            regression_run_id=regression_run_id,
            test_class=test_class,
            test_method=test_method,
            baseline_status=baseline_status,  # type: ignore[arg-type]
            regression_status=regression_status,  # type: ignore[arg-type]
            diff_type=diff_type,
        )
