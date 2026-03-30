"""ChangeComparisonService 测试."""

from jcia.core.entities.test_run import (
    CoverageData,
    RunType,
    TestResult,
    TestRun,
    TestStatus,
)


class TestChangeComparisonService:
    """ChangeComparisonService 测试类."""

    def test_compare_baseline_and_regression(self) -> None:
        """测试比较基线和回归测试."""
        from jcia.core.services import ChangeComparisonService

        # Arrange
        service = ChangeComparisonService()

        baseline = TestRun(
            id=1,
            run_type=RunType.BASELINE,
            commit_hash="abc123",
            test_results=[
                TestResult(
                    test_class="ServiceTest",
                    test_method="testMethod1",
                    status=TestStatus.PASSED,
                ),
                TestResult(
                    test_class="ServiceTest",
                    test_method="testMethod2",
                    status=TestStatus.PASSED,
                ),
            ],
        )

        regression = TestRun(
            id=2,
            run_type=RunType.REGRESSION,
            commit_hash="def456",
            test_results=[
                TestResult(
                    test_class="ServiceTest",
                    test_method="testMethod1",
                    status=TestStatus.PASSED,
                ),
                TestResult(
                    test_class="ServiceTest",
                    test_method="testMethod2",
                    status=TestStatus.FAILED,
                ),
            ],
        )

        # Act
        comparison = service.compare(baseline, regression)

        # Assert
        assert comparison is not None
        assert comparison.baseline_run == baseline
        assert comparison.regression_run == regression

    def test_detect_new_failures(self) -> None:
        """测试检测新增失败."""
        from jcia.core.services import ChangeComparisonService

        # Arrange
        service = ChangeComparisonService()

        baseline = TestRun(
            id=1,
            run_type=RunType.BASELINE,
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="testMethod",
                    status=TestStatus.PASSED,
                ),
            ],
        )

        regression = TestRun(
            id=2,
            run_type=RunType.REGRESSION,
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="testMethod",
                    status=TestStatus.FAILED,
                ),
            ],
        )

        # Act
        comparison = service.compare(baseline, regression)

        # Assert
        assert len(comparison.new_failures) > 0
        assert comparison.has_regression_issues

    def test_detect_new_passes(self) -> None:
        """测试检测新增通过."""
        from jcia.core.services import ChangeComparisonService

        # Arrange
        service = ChangeComparisonService()

        baseline = TestRun(
            id=1,
            run_type=RunType.BASELINE,
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="testMethod",
                    status=TestStatus.FAILED,
                ),
            ],
        )

        regression = TestRun(
            id=2,
            run_type=RunType.REGRESSION,
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="testMethod",
                    status=TestStatus.PASSED,
                ),
            ],
        )

        # Act
        comparison = service.compare(baseline, regression)

        # Assert
        assert len(comparison.new_passes) > 0

    def test_handle_removed_tests(self) -> None:
        """测试处理移除的测试."""
        from jcia.core.services import ChangeComparisonService

        # Arrange
        service = ChangeComparisonService()

        baseline = TestRun(
            id=1,
            run_type=RunType.BASELINE,
            test_results=[
                TestResult(
                    test_class="OldTest",
                    test_method="testOld",
                    status=TestStatus.PASSED,
                ),
                TestResult(
                    test_class="NewTest",
                    test_method="testNew",
                    status=TestStatus.PASSED,
                ),
            ],
        )

        regression = TestRun(
            id=2,
            run_type=RunType.REGRESSION,
            test_results=[
                TestResult(
                    test_class="NewTest",
                    test_method="testNew",
                    status=TestStatus.PASSED,
                ),
            ],
        )

        # Act
        comparison = service.compare(baseline, regression)

        # Assert
        # 移除的测试应该有差异记录
        assert len(comparison.diffs) > 0

    def test_get_diff_summary(self) -> None:
        """测试获取差异摘要."""
        from jcia.core.services import ChangeComparisonService

        # Arrange
        service = ChangeComparisonService()

        baseline = TestRun(
            id=1,
            run_type=RunType.BASELINE,
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="test1",
                    status=TestStatus.PASSED,
                ),
                TestResult(
                    test_class="Test",
                    test_method="test2",
                    status=TestStatus.PASSED,
                ),
            ],
        )

        regression = TestRun(
            id=2,
            run_type=RunType.REGRESSION,
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="test1",
                    status=TestStatus.PASSED,
                ),
                TestResult(
                    test_class="Test",
                    test_method="test2",
                    status=TestStatus.FAILED,
                ),
            ],
        )

        # Act
        comparison = service.compare(baseline, regression)
        summary = service.get_diff_summary(comparison)

        # Assert
        assert "total_diffs" in summary
        assert "new_passes" in summary
        assert "new_failures" in summary
        assert "regression_issues" in summary

    def test_compare_with_none_baseline(self) -> None:
        """测试没有基线的情况."""
        from jcia.core.services import ChangeComparisonService

        # Arrange
        service = ChangeComparisonService()

        regression = TestRun(
            id=2,
            run_type=RunType.REGRESSION,
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="testMethod",
                    status=TestStatus.PASSED,
                ),
            ],
        )

        # Act
        comparison = service.compare(None, regression)

        # Assert
        assert comparison.regression_run == regression
        assert comparison.baseline_run is None

    def test_compare_with_coverage_diff(self) -> None:
        """测试包含覆盖率差异的比较."""
        from jcia.core.services import ChangeComparisonService

        # Arrange
        service = ChangeComparisonService()

        baseline = TestRun(
            id=1,
            run_type=RunType.BASELINE,
            coverage=CoverageData(line_coverage=80.0),
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="testMethod",
                    status=TestStatus.PASSED,
                ),
            ],
        )

        regression = TestRun(
            id=2,
            run_type=RunType.REGRESSION,
            coverage=CoverageData(line_coverage=75.0),
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="testMethod",
                    status=TestStatus.PASSED,
                ),
            ],
        )

        # Act
        service.compare(baseline, regression)
        coverage_diff = service.get_coverage_diff(baseline, regression)

        # Assert
        assert coverage_diff is not None
        assert "baseline" in coverage_diff
        assert "regression" in coverage_diff
        assert "diff" in coverage_diff

    def test_compare_with_none_regression(self) -> None:
        """测试没有回归测试的情况."""
        from jcia.core.services import ChangeComparisonService

        # Arrange
        service = ChangeComparisonService()

        baseline = TestRun(
            id=1,
            run_type=RunType.BASELINE,
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="testMethod",
                    status=TestStatus.PASSED,
                ),
            ],
        )

        # Act
        comparison = service.compare(baseline, None)

        # Assert
        assert comparison.baseline_run == baseline
        assert comparison.regression_run is None

    def test_compare_both_none(self) -> None:
        """测试基线和回归都为 None."""
        from jcia.core.services import ChangeComparisonService

        service = ChangeComparisonService()

        comparison = service.compare(None, None)

        assert comparison.baseline_run is None
        assert comparison.regression_run is None

    def test_get_coverage_diff_with_none_baseline(self) -> None:
        """测试覆盖率差异比较当 baseline 为 None."""
        from jcia.core.services import ChangeComparisonService

        service = ChangeComparisonService()

        regression = TestRun(
            id=2,
            run_type=RunType.REGRESSION,
            coverage=CoverageData(line_coverage=75.0),
            test_results=[],
        )

        coverage_diff = service.get_coverage_diff(None, regression)

        # 当 baseline 为 None 时，返回 None
        assert coverage_diff is None

    def test_get_coverage_diff_with_none_regression(self) -> None:
        """测试覆盖率差异比较当 regression 为 None."""
        from jcia.core.services import ChangeComparisonService

        service = ChangeComparisonService()

        baseline = TestRun(
            id=1,
            run_type=RunType.BASELINE,
            coverage=CoverageData(line_coverage=80.0),
            test_results=[],
        )

        coverage_diff = service.get_coverage_diff(baseline, None)

        # 当 regression 为 None 时，返回 None
        assert coverage_diff is None

    def test_detect_stable_fail(self) -> None:
        """测试检测持续失败."""
        from jcia.core.services import ChangeComparisonService

        service = ChangeComparisonService()

        baseline = TestRun(
            id=1,
            run_type=RunType.BASELINE,
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="testMethod",
                    status=TestStatus.FAILED,
                ),
            ],
        )

        regression = TestRun(
            id=2,
            run_type=RunType.REGRESSION,
            test_results=[
                TestResult(
                    test_class="Test",
                    test_method="testMethod",
                    status=TestStatus.FAILED,
                ),
            ],
        )

        comparison = service.compare(baseline, regression)

        # 持续失败的测试应该在 diffs 中
        assert len(comparison.diffs) > 0
