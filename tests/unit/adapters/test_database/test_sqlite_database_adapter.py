"""SQLiteDatabaseAdapter 单元测试."""

from jcia.adapters.database.sqlite_adapter import SQLiteDatabaseAdapter
from jcia.core.entities.test_run import DiffType, RunStatus, RunType, TestRun, TestStatus


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

    def test_factory_methods_create_entities(self) -> None:
        """测试工厂方法正确创建实体。"""
        adapter = SQLiteDatabaseAdapter(":memory:")

        # TestRun
        run = adapter.create_test_run("hash123", RunType.BASELINE, RunStatus.COMPLETED)
        assert run.commit_hash == "hash123"
        assert run.run_type == RunType.BASELINE
        assert run.status == RunStatus.COMPLETED

        # TestResult
        result = adapter.create_test_result(1, "ClassA", "methodA")
        assert result.test_run_id == 1
        assert result.test_class == "ClassA"
        assert result.test_method == "methodA"

        # TestDiff
        diff = adapter.create_test_diff(
            1, 2, "ClassB", "methodB", TestStatus.PASSED, TestStatus.FAILED, DiffType.NEW_FAIL
        )
        assert diff.baseline_run_id == 1
        assert diff.regression_run_id == 2
        assert diff.diff_type == DiffType.NEW_FAIL
        adapter.close()

    def test_repository_integration(self) -> None:
        """测试适配器集成的各个仓储是否正常工作。"""
        adapter = SQLiteDatabaseAdapter(":memory:")

        # 1. 保存 TestRun
        run = adapter.create_test_run("hash456")
        run_id = adapter.test_run_repo.save(run)
        assert run_id > 0

        # 2. 保存 TestResult
        result = adapter.create_test_result(run_id, "T", "m", status=TestStatus.PASSED)
        result_id = adapter.test_result_repo.save(result)
        assert result_id > 0

        # 3. 保存 TestDiff
        diff = adapter.create_test_diff(
            1, run_id, "T", "m", TestStatus.PASSED, TestStatus.PASSED, "STABLE_PASS"
        )
        diff_id = adapter.test_diff_repo.save(diff)
        assert diff_id > 0

        # 4. 验证级联查询（简单验证）
        results = adapter.test_result_repo.find_by_run_id(run_id)
        assert len(results) == 1
        assert results[0].test_run_id == run_id

        adapter.close()

    def test_delete_and_query(self) -> None:
        """测试删除记录和查询。"""
        adapter = SQLiteDatabaseAdapter(":memory:")
        run = adapter.create_test_run("hash123")
        run_id = adapter.test_run_repo.save(run)

        # Act
        adapter.test_run_repo.delete(run_id)

        # Assert
        result = adapter.test_run_repo.find_by_id(run_id)
        assert result is None

        adapter.close()

    def test_query_multiple_results(self) -> None:
        """测试查询多个结果。"""
        adapter = SQLiteDatabaseAdapter(":memory:")

        # 创建多个测试运行记录
        for i in range(10):
            run = adapter.create_test_run(f"commit{i}")
            adapter.test_run_repo.save(run)

        # Act - 使用 find_latest 来验证记录存在
        latest = adapter.test_run_repo.find_latest()

        # Assert
        assert latest is not None
        assert latest.commit_hash == "commit9"

        adapter.close()

    def test_query_by_commit_hash(self) -> None:
        """测试通过 commit hash 查询。"""
        adapter = SQLiteDatabaseAdapter(":memory:")

        # 创建多个测试运行
        base_run = adapter.create_test_run("base123")
        adapter.test_run_repo.save(base_run)

        # Act - 使用 find_by_commit
        results = adapter.test_run_repo.find_by_commit("base123")

        # Assert
        assert len(results) == 1
        assert results[0].commit_hash == "base123"

        adapter.close()

    def test_update_test_run(self) -> None:
        """测试更新测试运行记录。"""
        adapter = SQLiteDatabaseAdapter(":memory:")

        # 创建并保存
        run = adapter.create_test_run("hash123", RunType.BASELINE, RunStatus.RUNNING)
        run_id = adapter.test_run_repo.save(run)

        # 更新
        run.status = RunStatus.COMPLETED
        run.total_tests = 10
        run.passed_tests = 9
        run.failed_tests = 1

        # Act
        adapter.test_run_repo.update(run)

        # Assert
        fetched = adapter.test_run_repo.find_by_id(run_id)
        assert fetched is not None  # 确保找到记录
        assert fetched.status == RunStatus.COMPLETED
        assert fetched.total_tests == 10
        assert fetched.passed_tests == 9

        adapter.close()

    def test_multiple_test_results(self) -> None:
        """测试保存多个测试结果。"""
        adapter = SQLiteDatabaseAdapter(":memory:")

        run = adapter.create_test_run("hash123")
        run_id = adapter.test_run_repo.save(run)

        # 创建多个测试结果
        for i in range(5):
            result = adapter.create_test_result(
                run_id, f"TestClass{i}", f"testMethod{i}", status=TestStatus.PASSED
            )
            result_id = adapter.test_result_repo.save(result)
            assert result_id > 0

        # Act
        results = adapter.test_result_repo.find_by_run_id(run_id)

        # Assert
        assert len(results) == 5

        adapter.close()

    def test_test_diff_operations(self) -> None:
        """测试测试差异操作。"""
        adapter = SQLiteDatabaseAdapter(":memory:")

        # 创建两个测试运行
        baseline_run = adapter.create_test_run("base", RunType.BASELINE)
        baseline_id = adapter.test_run_repo.save(baseline_run)

        regression_run = adapter.create_test_run("reg", RunType.REGRESSION)
        regression_id = adapter.test_run_repo.save(regression_run)

        # 创建测试差异
        diff = adapter.create_test_diff(
            baseline_id,
            regression_id,
            "TestClass",
            "testMethod",
            TestStatus.PASSED,
            TestStatus.FAILED,
            DiffType.NEW_FAIL,
        )
        diff_id = adapter.test_diff_repo.save(diff)
        assert diff_id > 0

        # Act - 使用 find_by_run_ids
        diffs = adapter.test_diff_repo.find_by_run_ids(baseline_id, regression_id)

        # Assert
        assert len(diffs) == 1

        adapter.close()

    def test_empty_repository_queries(self) -> None:
        """测试空仓储的查询。"""
        adapter = SQLiteDatabaseAdapter(":memory:")

        # Act
        latest = adapter.test_run_repo.find_latest()
        results = adapter.test_result_repo.find_by_run_id(999)

        # Assert
        assert latest is None
        assert len(results) == 0

        adapter.close()

    def test_error_handling_closed_connection(self) -> None:
        """测试关闭连接后的错误处理。"""
        import pytest

        adapter = SQLiteDatabaseAdapter(":memory:")
        adapter.close()

        # Act & Assert - 应该抛出 RuntimeError
        with pytest.raises(RuntimeError, match="Database not connected"):
            adapter.test_run_repo.find_latest()
