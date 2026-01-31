"""SQLite 仓储实现单元测试."""

from collections.abc import Iterator
from datetime import datetime

import pytest

from jcia.core.entities.test_run import (
    RunStatus,
    RunType,
    TestDiff,
    TestResult,
    TestRun,
    TestStatus,
)
from jcia.infrastructure.database.sqlite_adapter import SQLiteAdapter
from jcia.infrastructure.database.sqlite_repository import (
    SQLiteTestDiffRepository,
    SQLiteTestResultRepository,
    SQLiteTestRunRepository,
)


@pytest.fixture
def adapter() -> Iterator[SQLiteAdapter]:
    """创建并连接内存数据库."""
    sqlite_adapter = SQLiteAdapter(":memory:")
    sqlite_adapter.connect()
    yield sqlite_adapter
    sqlite_adapter.disconnect()


@pytest.fixture
def run_repo(adapter: SQLiteAdapter) -> SQLiteTestRunRepository:
    """创建 TestRun 仓储."""
    return SQLiteTestRunRepository(adapter)


@pytest.fixture
def result_repo(adapter: SQLiteAdapter) -> SQLiteTestResultRepository:
    """创建 TestResult 仓储."""
    return SQLiteTestResultRepository(adapter)


@pytest.fixture
def diff_repo(adapter: SQLiteAdapter) -> SQLiteTestDiffRepository:
    """创建 TestDiff 仓储."""
    return SQLiteTestDiffRepository(adapter)


class TestSQLiteTestRunRepository:
    """SQLiteTestRunRepository 测试类."""

    def test_save_and_find_by_id(self, run_repo: SQLiteTestRunRepository) -> None:
        """测试保存并按ID查询."""
        # Arrange
        test_run = TestRun(
            run_type=RunType.BASELINE,
            commit_hash="abc123",
            status=RunStatus.COMPLETED,
            total_tests=10,
            passed_tests=9,
            failed_tests=1,
        )

        # Act
        run_id = run_repo.save(test_run)
        found = run_repo.find_by_id(run_id)

        # Assert
        assert run_id > 0
        assert found is not None
        assert found.commit_hash == "abc123"
        assert found.run_type == RunType.BASELINE
        assert found.status == RunStatus.COMPLETED

    def test_find_by_commit_with_run_type(self, run_repo: SQLiteTestRunRepository) -> None:
        """测试按提交与运行类型过滤."""
        # Arrange
        baseline = TestRun(run_type=RunType.BASELINE, commit_hash="same")
        regression = TestRun(run_type=RunType.REGRESSION, commit_hash="same")
        other = TestRun(run_type=RunType.BASELINE, commit_hash="other")

        run_repo.save(baseline)
        run_repo.save(regression)
        run_repo.save(other)

        # Act
        all_runs = run_repo.find_by_commit("same")
        baseline_runs = run_repo.find_by_commit("same", run_type=RunType.BASELINE.value)

        # Assert
        assert len(all_runs) == 2
        assert len(baseline_runs) == 1
        assert baseline_runs[0].run_type == RunType.BASELINE

    def test_find_latest_returns_newest(self, run_repo: SQLiteTestRunRepository) -> None:
        """测试获取最新运行."""
        # Arrange
        older = TestRun(commit_hash="c1", timestamp=datetime(2024, 1, 1, 0, 0, 0))
        newer = TestRun(commit_hash="c2", timestamp=datetime(2024, 1, 2, 0, 0, 0))
        run_repo.save(older)
        run_repo.save(newer)

        # Act
        latest = run_repo.find_latest()

        # Assert
        assert latest is not None
        assert latest.commit_hash == "c2"

    def test_update_and_delete(self, run_repo: SQLiteTestRunRepository) -> None:
        """测试更新与删除."""
        # Arrange
        test_run = TestRun(commit_hash="c3", status=RunStatus.PENDING)
        run_id = run_repo.save(test_run)
        test_run.id = run_id
        test_run.status = RunStatus.COMPLETED

        # Act
        updated = run_repo.update(test_run)
        deleted = run_repo.delete(run_id)

        # Assert
        assert updated is True
        assert deleted is True
        assert run_repo.find_by_id(run_id) is None


class TestSQLiteTestResultRepository:
    """SQLiteTestResultRepository 测试类."""

    def test_save_and_find_by_run_id(
        self,
        run_repo: SQLiteTestRunRepository,
        result_repo: SQLiteTestResultRepository,
    ) -> None:
        """测试保存并按运行ID查询结果."""
        # Arrange
        run_id = run_repo.save(TestRun(commit_hash="c1"))
        result = TestResult(
            test_run_id=run_id,
            test_class="DemoTest",
            test_method="test_ok",
            status=TestStatus.PASSED,
            duration_ms=12,
        )

        # Act
        result_id = result_repo.save(result)
        results = result_repo.find_by_run_id(run_id)

        # Assert
        assert result_id > 0
        assert len(results) == 1
        assert results[0].test_class == "DemoTest"
        assert results[0].status == TestStatus.PASSED

    def test_save_batch_returns_count(
        self,
        run_repo: SQLiteTestRunRepository,
        result_repo: SQLiteTestResultRepository,
    ) -> None:
        """测试批量保存返回数量."""
        # Arrange
        run_id = run_repo.save(TestRun(commit_hash="c2"))
        results = [
            TestResult(test_run_id=run_id, test_class="T", test_method="a"),
            TestResult(test_run_id=run_id, test_class="T", test_method="b"),
        ]

        # Act
        count = result_repo.save_batch(results)

        # Assert
        assert count == 2

    def test_find_failed_by_run_id(
        self,
        run_repo: SQLiteTestRunRepository,
        result_repo: SQLiteTestResultRepository,
    ) -> None:
        """测试查询失败结果."""
        # Arrange
        run_id = run_repo.save(TestRun(commit_hash="c3"))
        result_repo.save(
            TestResult(
                test_run_id=run_id,
                test_class="T",
                test_method="pass",
                status=TestStatus.PASSED,
            )
        )
        result_repo.save(
            TestResult(
                test_run_id=run_id,
                test_class="T",
                test_method="fail",
                status=TestStatus.FAILED,
            )
        )

        # Act
        failed = result_repo.find_failed_by_run_id(run_id)

        # Assert
        assert len(failed) == 1
        assert failed[0].status == TestStatus.FAILED


class TestSQLiteTestDiffRepository:
    """SQLiteTestDiffRepository 测试类."""

    def test_save_and_find_by_run_ids(
        self,
        diff_repo: SQLiteTestDiffRepository,
    ) -> None:
        """测试保存并按运行ID查询差异."""
        # Arrange
        diff = TestDiff(
            baseline_run_id=1,
            regression_run_id=2,
            test_class="DemoTest",
            test_method="test_case",
            baseline_status=TestStatus.PASSED,
            regression_status=TestStatus.FAILED,
            diff_type="NEW_FAIL",
        )

        # Act
        diff_id = diff_repo.save(diff)
        diffs = diff_repo.find_by_run_ids(1, 2)

        # Assert
        assert diff_id > 0
        assert len(diffs) == 1
        assert diffs[0].diff_type == "NEW_FAIL"

    def test_find_unexpected_failures(self, diff_repo: SQLiteTestDiffRepository) -> None:
        """测试查询非预期失败."""
        # Arrange
        diff_repo.save(
            TestDiff(
                baseline_run_id=10,
                regression_run_id=11,
                test_class="DemoTest",
                test_method="case1",
                baseline_status=TestStatus.PASSED,
                regression_status=TestStatus.FAILED,
                diff_type="NEW_FAIL",
            )
        )
        diff_repo.save(
            TestDiff(
                baseline_run_id=10,
                regression_run_id=11,
                test_class="DemoTest",
                test_method="case2",
                baseline_status=TestStatus.FAILED,
                regression_status=TestStatus.FAILED,
                diff_type="STABLE_FAIL",
            )
        )

        # Act
        unexpected = diff_repo.find_unexpected_failures(10, 11)

        # Assert
        assert len(unexpected) == 1
        assert unexpected[0].test_method == "case1"
