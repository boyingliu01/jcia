"""SQLiteDatabaseAdapter 单元测试."""

from jcia.adapters.database.sqlite_adapter import SQLiteDatabaseAdapter
from jcia.core.entities.test_run import RunStatus, RunType, TestRun


class TestSQLiteDatabaseAdapter:
    """SQLiteDatabaseAdapter 测试类."""

    def test_connect_and_repositories_available(self) -> None:
        """初始化后应已连接并暴露仓储."""
        adapter = SQLiteDatabaseAdapter(":memory:")

        assert adapter.is_connected is True
        assert adapter.test_run_repo is not None
        assert adapter.test_result_repo is not None
        assert adapter.test_diff_repo is not None

        adapter.close()
        assert adapter.is_connected is False

    def test_save_and_fetch_test_run(self) -> None:
        """能够保存并读取测试运行记录."""
        adapter = SQLiteDatabaseAdapter(":memory:")

        run = TestRun(
            commit_hash="abc123",
            run_type=RunType.BASELINE,
            status=RunStatus.COMPLETED,
            total_tests=1,
            passed_tests=1,
        )
        run_id = adapter.test_run_repo.save(run)
        fetched = adapter.test_run_repo.find_by_id(run_id)

        assert fetched is not None
        assert fetched.commit_hash == "abc123"
        assert fetched.run_type == RunType.BASELINE
        adapter.close()
