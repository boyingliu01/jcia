"""SQLite 仓储实现."""

import json
from datetime import datetime
from typing import Any

from jcia.core.entities.test_run import (
    CoverageData,
    DiffType,
    RunStatus,
    RunType,
    TestDiff,
    TestResult,
    TestRun,
    TestStatus,
)
from jcia.core.interfaces.repository import (
    TestDiffRepository,
    TestResultRepository,
    TestRunRepository,
)
from jcia.infrastructure.database.sqlite_adapter import SQLiteAdapter


class SQLiteTestRunRepository(TestRunRepository):
    """SQLite TestRun 仓储实现."""

    def __init__(self, adapter: SQLiteAdapter) -> None:
        """初始化仓储.

        Args:
            adapter: SQLite 适配器
        """
        self._adapter = adapter
        if not self._adapter.is_connected():
            self._adapter.connect()

    def save(self, test_run: TestRun) -> int:
        """保存测试运行记录."""
        row_id = self._adapter.execute_write(
            """
            INSERT INTO test_runs (
                commit_hash,
                commit_message,
                branch_name,
                run_type,
                start_time,
                end_time,
                status,
                total_tests,
                passed_tests,
                failed_tests,
                skipped_tests,
                error_tests,
                total_duration_ms,
                coverage_json,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_run.commit_hash,
                test_run.commit_message,
                test_run.branch_name,
                test_run.run_type.value,
                test_run.timestamp.isoformat() if test_run.timestamp else None,
                None,
                test_run.status.value,
                test_run.total_tests,
                test_run.passed_tests,
                test_run.failed_tests,
                test_run.skipped_tests,
                test_run.error_tests,
                test_run.total_duration_ms,
                json.dumps(test_run.coverage.__dict__) if test_run.coverage else None,
                json.dumps(test_run.metadata) if test_run.metadata else None,
            ),
        )
        test_run.id = row_id
        return row_id

    def find_by_id(self, run_id: int) -> TestRun | None:
        """根据ID查询测试运行."""
        rows = self._adapter.execute(
            """
            SELECT id, commit_hash, commit_message, branch_name, run_type, start_time,
                   end_time, status, total_tests, passed_tests, failed_tests,
                   skipped_tests, error_tests, total_duration_ms, coverage_json,
                   metadata_json
              FROM test_runs
             WHERE id = ?
            """,
            (run_id,),
        )

        if not rows:
            return None
        return _row_to_test_run(rows[0])

    def find_by_commit(self, commit_hash: str, run_type: str | None = None) -> list[TestRun]:
        """根据提交哈希查询测试运行."""
        if run_type:
            rows = self._adapter.execute(
                """
                SELECT id, commit_hash, commit_message, branch_name, run_type,
                       start_time, end_time, status, total_tests, passed_tests,
                       failed_tests, skipped_tests, error_tests, total_duration_ms,
                       coverage_json, metadata_json
                  FROM test_runs
                 WHERE commit_hash = ? AND run_type = ?
                """,
                (commit_hash, run_type),
            )
        else:
            rows = self._adapter.execute(
                """
                SELECT id, commit_hash, commit_message, branch_name, run_type,
                       start_time, end_time, status, total_tests, passed_tests,
                       failed_tests, skipped_tests, error_tests, total_duration_ms,
                       coverage_json, metadata_json
                  FROM test_runs
                 WHERE commit_hash = ?
                """,
                (commit_hash,),
            )

        return [_row_to_test_run(row) for row in rows]

    def find_latest(self, run_type: str | None = None) -> TestRun | None:
        """查询最新的测试运行."""
        if run_type:
            rows = self._adapter.execute(
                """
                SELECT id, commit_hash, commit_message, branch_name, run_type,
                       start_time, end_time, status, total_tests, passed_tests,
                       failed_tests, skipped_tests, error_tests, total_duration_ms,
                       coverage_json, metadata_json
                  FROM test_runs
                 WHERE run_type = ?
                 ORDER BY start_time DESC
                 LIMIT 1
                """,
                (run_type,),
            )
        else:
            rows = self._adapter.execute(
                """
                SELECT id, commit_hash, commit_message, branch_name, run_type,
                       start_time, end_time, status, total_tests, passed_tests,
                       failed_tests, skipped_tests, error_tests, total_duration_ms,
                       coverage_json, metadata_json
                  FROM test_runs
                 ORDER BY start_time DESC
                 LIMIT 1
                """,
                (),
            )

        if not rows:
            return None
        return _row_to_test_run(rows[0])

    def update(self, test_run: TestRun) -> bool:
        """更新测试运行记录."""
        if test_run.id is None:
            return False
        affected = self._adapter.execute_non_query(
            """
            UPDATE test_runs
               SET commit_hash = ?,
                   commit_message = ?,
                   branch_name = ?,
                   run_type = ?,
                   start_time = ?,
                   status = ?,
                   total_tests = ?,
                   passed_tests = ?,
                   failed_tests = ?,
                   skipped_tests = ?,
                   error_tests = ?,
                   total_duration_ms = ?,
                   coverage_json = ?,
                   metadata_json = ?
             WHERE id = ?
            """,
            (
                test_run.commit_hash,
                test_run.commit_message,
                test_run.branch_name,
                test_run.run_type.value,
                test_run.timestamp.isoformat() if test_run.timestamp else None,
                test_run.status.value,
                test_run.total_tests,
                test_run.passed_tests,
                test_run.failed_tests,
                test_run.skipped_tests,
                test_run.error_tests,
                test_run.total_duration_ms,
                json.dumps(test_run.coverage.__dict__) if test_run.coverage else None,
                json.dumps(test_run.metadata) if test_run.metadata else None,
                test_run.id,
            ),
        )
        return affected > 0

    def delete(self, run_id: int) -> bool:
        """删除测试运行记录."""
        affected = self._adapter.execute_non_query(
            "DELETE FROM test_runs WHERE id = ?",
            (run_id,),
        )
        return affected > 0


class SQLiteTestResultRepository(TestResultRepository):
    """SQLite TestResult 仓储实现."""

    def __init__(self, adapter: SQLiteAdapter) -> None:
        """初始化仓储.

        Args:
            adapter: SQLite 适配器
        """
        self._adapter = adapter
        if not self._adapter.is_connected():
            self._adapter.connect()

    def save(self, test_result: TestResult) -> int:
        """保存测试结果."""
        row_id = self._adapter.execute_write(
            """
            INSERT INTO test_results (
                run_id,
                test_class,
                test_method,
                status,
                duration_ms,
                error_message,
                stack_trace,
                coverage_data_json,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_result.test_run_id,
                test_result.test_class,
                test_result.test_method,
                test_result.status.value,
                test_result.duration_ms,
                test_result.error_message,
                test_result.stack_trace,
                json.dumps(test_result.coverage_data.__dict__)
                if test_result.coverage_data
                else None,
                test_result.timestamp.isoformat() if test_result.timestamp else None,
            ),
        )
        test_result.id = row_id
        return row_id

    def save_batch(self, results: list[TestResult]) -> int:
        """批量保存测试结果."""
        if not results:
            return 0

        rows = [
            (
                r.test_run_id,
                r.test_class,
                r.test_method,
                r.status.value,
                r.duration_ms,
                r.error_message,
                r.stack_trace,
                json.dumps(r.coverage_data.__dict__) if r.coverage_data else None,
                r.timestamp.isoformat() if r.timestamp else None,
            )
            for r in results
        ]

        connection = self._adapter._connection
        if connection is None:
            raise RuntimeError("Database not connected")

        cursor = connection.cursor()
        cursor.executemany(
            """
            INSERT INTO test_results (
                run_id,
                test_class,
                test_method,
                status,
                duration_ms,
                error_message,
                stack_trace,
                coverage_data_json,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()
        rowcount = cursor.rowcount or 0
        cursor.close()
        return int(rowcount)

    def find_by_run_id(self, run_id: int) -> list[TestResult]:
        """根据运行ID查询测试结果."""
        rows = self._adapter.execute(
            """
            SELECT id, run_id, test_class, test_method, status, duration_ms,
                   error_message, stack_trace, coverage_data_json, timestamp
              FROM test_results
             WHERE run_id = ?
            """,
            (run_id,),
        )
        return [_row_to_test_result(row) for row in rows]

    def find_failed_by_run_id(self, run_id: int) -> list[TestResult]:
        """查询指定运行的失败测试."""
        rows = self._adapter.execute(
            """
            SELECT id, run_id, test_class, test_method, status, duration_ms,
                   error_message, stack_trace, coverage_data_json, timestamp
              FROM test_results
             WHERE run_id = ? AND status IN (?, ?)
            """,
            (run_id, TestStatus.FAILED.value, TestStatus.ERROR.value),
        )
        return [_row_to_test_result(row) for row in rows]


class SQLiteTestDiffRepository(TestDiffRepository):
    """SQLite TestDiff 仓储实现."""

    def __init__(self, adapter: SQLiteAdapter) -> None:
        """初始化仓储.

        Args:
            adapter: SQLite 适配器
        """
        self._adapter = adapter
        if not self._adapter.is_connected():
            self._adapter.connect()

    def save(self, test_diff: TestDiff) -> int:
        """保存测试差异."""
        row_id = self._adapter.execute_write(
            """
            INSERT INTO test_diffs (
                baseline_run_id,
                regression_run_id,
                test_class,
                test_method,
                baseline_status,
                regression_status,
                diff_type,
                analysis_result,
                analysis_reason,
                reviewed_by,
                reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_diff.baseline_run_id,
                test_diff.regression_run_id,
                test_diff.test_class,
                test_diff.test_method,
                test_diff.baseline_status.value if test_diff.baseline_status else None,
                test_diff.regression_status.value if test_diff.regression_status else None,
                test_diff.diff_type.value,
                test_diff.analysis_result,
                test_diff.analysis_reason,
                test_diff.reviewed_by,
                test_diff.reviewed_at.isoformat() if test_diff.reviewed_at else None,
            ),
        )

        test_diff.id = row_id
        return row_id

    def save_batch(self, diffs: list[TestDiff]) -> int:
        """批量保存测试差异（单事务批量插入）."""
        if not diffs:
            return 0

        rows = [
            (
                diff.baseline_run_id,
                diff.regression_run_id,
                diff.test_class,
                diff.test_method,
                diff.baseline_status.value if diff.baseline_status else None,
                diff.regression_status.value if diff.regression_status else None,
                diff.diff_type.value,
                diff.analysis_result,
                diff.analysis_reason,
                diff.reviewed_by,
                diff.reviewed_at.isoformat() if diff.reviewed_at else None,
            )
            for diff in diffs
        ]

        connection = self._adapter._connection
        if connection is None:
            raise RuntimeError("Database not connected")

        cursor = connection.cursor()
        cursor.executemany(
            """
            INSERT INTO test_diffs (
                baseline_run_id,
                regression_run_id,
                test_class,
                test_method,
                baseline_status,
                regression_status,
                diff_type,
                analysis_result,
                analysis_reason,
                reviewed_by,
                reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()
        rowcount = cursor.rowcount or 0
        cursor.close()
        return int(rowcount)

    def find_by_run_ids(self, baseline_run_id: int, regression_run_id: int) -> list[TestDiff]:
        """根据基线和回归运行ID查询差异."""
        rows = self._adapter.execute(
            """
            SELECT id, baseline_run_id, regression_run_id, test_class, test_method,
                   baseline_status, regression_status, diff_type, analysis_result,
                   analysis_reason, reviewed_by, reviewed_at
              FROM test_diffs
             WHERE baseline_run_id = ? AND regression_run_id = ?
            """,
            (baseline_run_id, regression_run_id),
        )

        return [_row_to_test_diff(row) for row in rows]

    def find_unexpected_failures(
        self, baseline_run_id: int, regression_run_id: int
    ) -> list[TestDiff]:
        """查询非预期的失败（基线通过，回归失败）."""
        rows = self._adapter.execute(
            """
            SELECT id, baseline_run_id, regression_run_id, test_class, test_method,
                   baseline_status, regression_status, diff_type, analysis_result,
                   analysis_reason, reviewed_by, reviewed_at
              FROM test_diffs
             WHERE baseline_run_id = ?
               AND regression_run_id = ?
               AND baseline_status = ?
               AND regression_status IN (?, ?)
            """,
            (
                baseline_run_id,
                regression_run_id,
                TestStatus.PASSED.value,
                TestStatus.FAILED.value,
                TestStatus.ERROR.value,
            ),
        )

        return [_row_to_test_diff(row) for row in rows]


def _row_to_test_run(row: tuple[Any, ...]) -> TestRun:
    """将查询行转换为 TestRun."""
    # 假设查询包含了所有新字段，按顺序解析
    # 如果 find_by_id 等方法还没有更新 SELECT 语句，这里会报错，所以需要同步更新 find 方法
    # 目前先根据 save 的字段顺序调整查询和解析
    return TestRun(
        id=_to_int(row[0]),
        commit_hash=str(row[1]),
        commit_message=str(row[2]) if row[2] else None,
        branch_name=str(row[3]) if row[3] else None,
        run_type=_safe_run_type(row[4]),
        timestamp=_parse_datetime(row[5]),
        status=_safe_run_status(row[7]),  # row[6] 是 end_time
        total_tests=_to_int(row[8]),
        passed_tests=_to_int(row[9]),
        failed_tests=_to_int(row[10]),
        skipped_tests=_to_int(row[11]),
        error_tests=_to_int(row[12]),
        total_duration_ms=_to_int(row[13]),
        coverage=_parse_coverage_json(row[14]),
        metadata=json.loads(str(row[15])) if row[15] else {},
    )


def _parse_coverage_json(data: Any) -> CoverageData | None:
    """解析覆盖率 JSON."""
    if not data:
        return None
    try:
        d = json.loads(str(data))
        return CoverageData(**d)
    except Exception:
        return None


def _row_to_test_result(row: tuple[Any, ...]) -> TestResult:
    """将查询行转换为 TestResult."""
    return TestResult(
        id=_to_int(row[0]),
        test_run_id=_to_int(row[1]),
        test_class=str(row[2]),
        test_method=str(row[3]),
        status=_safe_test_status_required(row[4]),
        duration_ms=_to_int(row[5]),
        error_message=str(row[6]) if row[6] else None,
        stack_trace=str(row[7]) if row[7] else None,
        coverage_data=_parse_coverage_json(row[8]),
        timestamp=_parse_datetime(row[9]),
    )


def _row_to_test_diff(row: tuple[object, ...]) -> TestDiff:
    """将查询行转换为 TestDiff."""
    (
        diff_id,
        baseline_run_id,
        regression_run_id,
        test_class,
        test_method,
        baseline_status,
        regression_status,
        diff_type,
        analysis_result,
        analysis_reason,
        reviewed_by,
        reviewed_at,
    ) = row
    return TestDiff(
        id=_to_int(diff_id),
        baseline_run_id=_to_int(baseline_run_id),
        regression_run_id=_to_int(regression_run_id),
        test_class=str(test_class),
        test_method=str(test_method),
        baseline_status=_safe_test_status(baseline_status),
        regression_status=_safe_test_status(regression_status),
        diff_type=_safe_diff_type(diff_type),
        analysis_result=str(analysis_result) if analysis_result is not None else "PENDING",
        analysis_reason=analysis_reason if analysis_reason is None else str(analysis_reason),
        reviewed_by=reviewed_by if reviewed_by is None else str(reviewed_by),
        reviewed_at=_parse_optional_datetime(reviewed_at),
    )


def _safe_diff_type(value: object | None) -> DiffType:
    """安全解析差异类型，默认返回 STABLE_PASS."""
    if isinstance(value, DiffType):
        return value
    if value is None:
        return DiffType.STABLE_PASS
    try:
        return DiffType(str(value))
    except ValueError:
        return DiffType.STABLE_PASS


def _parse_datetime(value: object) -> datetime:
    """解析时间字符串."""

    if isinstance(value, datetime):
        return value
    if value is None:
        return datetime.now()
    return datetime.fromisoformat(str(value))


def _parse_optional_datetime(value: object) -> datetime | None:
    """解析可选时间字符串."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _to_int(value: object | None) -> int:
    """安全转换为 int."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float | str):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    return 0


def _safe_run_type(value: object) -> RunType:
    """安全解析运行类型."""
    try:
        return RunType(str(value))
    except ValueError:
        return RunType.REGRESSION


def _safe_run_status(value: object) -> RunStatus:
    """安全解析运行状态."""
    try:
        return RunStatus(str(value))
    except ValueError:
        return RunStatus.PENDING


def _safe_test_status(value: object, allow_none: bool = True) -> TestStatus | None:
    """安全解析测试状态."""
    if value is None:
        return None if allow_none else TestStatus.PENDING
    try:
        return TestStatus(str(value))
    except ValueError:
        return TestStatus.PENDING


def _safe_test_status_required(value: object) -> TestStatus:
    """安全解析必需的测试状态，默认回退 PENDING."""
    result = _safe_test_status(value, allow_none=True)
    return result if result is not None else TestStatus.PENDING
