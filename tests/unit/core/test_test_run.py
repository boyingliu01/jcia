"""TestRun领域实体单元测试."""

import pytest

from jcia.core.entities.test_run import (
    CoverageData,
    RunType,
    TestComparison,
    TestDiff,
    TestResult,
    TestRun,
    TestStatus,
)


class TestCoverageData:
    """CoverageData测试类."""

    def test_coverage_ratio(self) -> None:
        """测试覆盖率比例."""
        high = CoverageData(line_coverage=80.0)
        zero = CoverageData(line_coverage=0.0)

        assert high.coverage_ratio == 0.8
        assert zero.coverage_ratio == 0.0


class TestTestResult:
    """TestResult测试类."""

    def test_full_name(self) -> None:
        """测试全限定名."""
        result = TestResult(
            test_class="com.example.Test",
            test_method="testSomething",
        )
        assert result.full_name == "com.example.Test#testSomething"

    def test_passed(self) -> None:
        """测试通过判断."""
        passed = TestResult(status=TestStatus.PASSED)
        failed = TestResult(status=TestStatus.FAILED)

        assert passed.passed is True
        assert failed.passed is False

    def test_failed(self) -> None:
        """测试失败判断."""
        failed = TestResult(status=TestStatus.FAILED)
        passed = TestResult(status=TestStatus.PASSED)

        assert failed.failed is True
        assert passed.failed is False


class TestTestRun:
    """TestRun测试类."""

    @pytest.fixture
    def sample_run(self) -> TestRun:
        """创建示例测试运行."""
        run = TestRun(
            id=1,
            run_type=RunType.REGRESSION,
            commit_hash="abcdef123456",
            commit_message="Test commit",
            branch_name="main",
        )
        return run

    def test_short_commit_hash(self, sample_run: TestRun) -> None:
        """测试短哈希."""
        assert sample_run.short_commit_hash == "abcdef1"

    def test_is_baseline(self) -> None:
        """测试基线判断."""
        baseline = TestRun(run_type=RunType.BASELINE)
        regression = TestRun(run_type=RunType.REGRESSION)

        assert baseline.is_baseline is True
        assert regression.is_baseline is False

    def test_is_regression(self) -> None:
        """测试回归判断."""
        baseline = TestRun(run_type=RunType.BASELINE)
        regression = TestRun(run_type=RunType.REGRESSION)

        assert regression.is_regression is True
        assert baseline.is_regression is False

    def test_success_rate(self, sample_run: TestRun) -> None:
        """测试成功率."""
        # 添加测试结果
        sample_run.add_results(
            [
                TestResult(test_class="T1", test_method="m1", status=TestStatus.PASSED),
                TestResult(test_class="T1", test_method="m2", status=TestStatus.PASSED),
                TestResult(test_class="T1", test_method="m3", status=TestStatus.FAILED),
            ]
        )

        assert sample_run.success_rate == 2 / 3

    def test_has_failures(self, sample_run: TestRun) -> None:
        """测试失败判断."""
        no_failures = TestRun()
        with_failures = TestRun()
        with_failures.failed_tests = 2

        assert no_failures.has_failures is False
        assert with_failures.has_failures is True

    def test_add_result_updates_counts(self, sample_run: TestRun) -> None:
        """测试添加结果更新计数."""
        sample_run.add_result(TestResult(status=TestStatus.PASSED))
        sample_run.add_result(TestResult(status=TestStatus.PASSED))
        sample_run.add_result(TestResult(status=TestStatus.FAILED))

        assert sample_run.total_tests == 3
        assert sample_run.passed_tests == 2
        assert sample_run.failed_tests == 1

    def test_get_failed_results(self) -> None:
        """测试获取失败结果."""
        run = TestRun()
        run.add_results(
            [
                TestResult(test_class="T", test_method="m1", status=TestStatus.PASSED),
                TestResult(test_class="T", test_method="m2", status=TestStatus.FAILED),
                TestResult(test_class="T", test_method="m3", status=TestStatus.FAILED),
            ]
        )

        failed = run.get_failed_results()
        assert len(failed) == 2
        assert all(r.failed for r in failed)

    def test_get_result_by_name(self) -> None:
        """测试按名称获取结果."""
        run = TestRun()
        run.add_result(
            TestResult(
                test_class="TestClass",
                test_method="testMethod",
                status=TestStatus.PASSED,
            )
        )

        found = run.get_result_by_name("TestClass#testMethod")
        not_found = run.get_result_by_name("NotFound#method")

        assert found is not None
        assert not_found is None


class TestTestDiff:
    """TestDiff测试类."""

    def test_full_name(self) -> None:
        """测试全限定名."""
        diff = TestDiff(
            test_class="com.Test",
            test_method="testMethod",
        )
        assert diff.full_name == "com.Test#testMethod"

    def test_is_new_pass(self) -> None:
        """测试新增通过."""
        new_pass = TestDiff(diff_type="NEW_PASS")
        not_new = TestDiff(diff_type="STABLE_PASS")

        assert new_pass.is_new_pass is True
        assert not_new.is_new_pass is False

    def test_is_new_fail(self) -> None:
        """测试新增失败."""
        new_fail = TestDiff(diff_type="NEW_FAIL")
        not_new = TestDiff(diff_type="STABLE_FAIL")

        assert new_fail.is_new_fail is True
        assert not_new.is_new_fail is False

    def test_is_regression_issue(self) -> None:
        """测试回归问题判断."""
        regression = TestDiff(
            baseline_status=TestStatus.PASSED,
            regression_status=TestStatus.FAILED,
        )
        stable = TestDiff(
            baseline_status=TestStatus.PASSED,
            regression_status=TestStatus.PASSED,
        )

        assert regression.is_regression_issue is True
        assert stable.is_regression_issue is False


class TestTestComparison:
    """TestComparison测试类."""

    @pytest.fixture
    def sample_comparison(self) -> TestComparison:
        """创建示例对比."""
        baseline = TestRun(id=1, run_type=RunType.BASELINE)
        regression = TestRun(id=2, run_type=RunType.REGRESSION)

        diffs = [
            TestDiff(diff_type="STABLE_PASS"),
            TestDiff(diff_type="NEW_PASS"),
            TestDiff(diff_type="NEW_FAIL"),
            TestDiff(diff_type="NEW_FAIL"),
        ]

        return TestComparison(
            baseline_run=baseline,
            regression_run=regression,
            diffs=diffs,
        )

    def test_new_passes(self, sample_comparison: TestComparison) -> None:
        """测试新增通过."""
        assert len(sample_comparison.new_passes) == 1

    def test_new_failures(self, sample_comparison: TestComparison) -> None:
        """测试新增失败."""
        assert len(sample_comparison.new_failures) == 2

    def test_has_regression_issues(self) -> None:
        """测试是否有回归问题."""
        with_issue = TestComparison(
            diffs=[
                TestDiff(
                    baseline_status=TestStatus.PASSED,
                    regression_status=TestStatus.FAILED,
                ),
            ]
        )
        no_issue = TestComparison(
            diffs=[
                TestDiff(
                    baseline_status=TestStatus.PASSED,
                    regression_status=TestStatus.PASSED,
                ),
            ]
        )

        assert with_issue.has_regression_issues is True
        assert no_issue.has_regression_issues is False

    def test_to_dict(self, sample_comparison: TestComparison) -> None:
        """测试转换为字典."""
        data = sample_comparison.to_dict()

        assert data["baseline"] is not None
        assert data["regression"] is not None
        assert data["diff_summary"]["total_diffs"] == 4
        assert data["diff_summary"]["new_passes"] == 1
        assert data["diff_summary"]["new_failures"] == 2
