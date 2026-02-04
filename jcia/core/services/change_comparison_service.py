"""变更比较领域服务.

比较基线测试和回归测试的结果，检测回归问题。
"""

from typing import Any

from jcia.core.entities.test_run import (
    DiffType,
    TestComparison,
    TestDiff,
    TestResult,
    TestRun,
    TestStatus,
)


class ChangeComparisonService:
    """变更比较服务.

    比较基线测试和回归测试的结果，识别回归问题。
    """

    def compare(self, baseline: TestRun | None, regression: TestRun | None) -> TestComparison:
        """比较基线和回归测试结果.

        Args:
            baseline: 基线测试运行
            regression: 回归测试运行

        Returns:
            TestComparison: 测试对比结果
        """
        comparison = TestComparison(
            baseline_run=baseline,
            regression_run=regression,
        )

        if regression is None:
            return comparison

        if baseline is None:
            # 没有基线，所有测试都视为新测试
            for result in regression.test_results:
                diff = TestDiff(
                    regression_run_id=regression.id or 0,
                    test_class=result.test_class,
                    test_method=result.test_method,
                    regression_status=result.status,
                    diff_type=DiffType.STABLE_PASS if result.passed else DiffType.STABLE_FAIL,
                )
                comparison.diffs.append(diff)
            return comparison

        # 比较每个测试的结果
        baseline_results_map = {r.full_name: r for r in baseline.test_results}

        for regression_result in regression.test_results:
            test_name = regression_result.full_name
            baseline_result = baseline_results_map.get(test_name)

            diff = self._create_diff(baseline_result, regression_result, baseline, regression)
            comparison.diffs.append(diff)

        # 检测移除的测试（基线有但回归没有）
        for baseline_result in baseline.test_results:
            test_name = baseline_result.full_name
            if test_name not in baseline_results_map:
                continue

            # 检查是否在回归测试中
            in_regression = any(r.full_name == test_name for r in regression.test_results)
            if not in_regression:
                diff = TestDiff(
                    baseline_run_id=baseline.id or 0,
                    test_class=baseline_result.test_class,
                    test_method=baseline_result.test_method,
                    baseline_status=baseline_result.status,
                    diff_type=DiffType.REMOVED,
                    analysis_result="REMOVED",
                    analysis_reason="Test removed in regression run",
                )
                comparison.diffs.append(diff)

        return comparison

    def get_diff_summary(self, comparison: TestComparison) -> dict[str, Any]:
        """获取差异摘要.

        Args:
            comparison: 测试对比结果

        Returns:
            Dict[str, Any]: 差异摘要
        """
        return {
            "total_diffs": len(comparison.diffs),
            "new_passes": len(comparison.new_passes),
            "new_failures": len(comparison.new_failures),
            "regression_issues": len(comparison.regression_issues),
            "has_regression": comparison.has_regression_issues,
        }

    def get_coverage_diff(
        self, baseline: TestRun | None, regression: TestRun | None
    ) -> dict[str, Any] | None:
        """获取覆盖率差异.

        Args:
            baseline: 基线测试运行
            regression: 回归测试运行

        Returns:
            Optional[Dict[str, Any]]: 覆盖率差异
        """
        if baseline is None or regression is None:
            return None

        baseline_coverage = baseline.coverage
        regression_coverage = regression.coverage

        if baseline_coverage is None or regression_coverage is None:
            return None

        return {
            "baseline": {
                "line_coverage": baseline_coverage.line_coverage,
                "branch_coverage": baseline_coverage.branch_coverage,
                "method_coverage": baseline_coverage.method_coverage,
                "class_coverage": baseline_coverage.class_coverage,
            },
            "regression": {
                "line_coverage": regression_coverage.line_coverage,
                "branch_coverage": regression_coverage.branch_coverage,
                "method_coverage": regression_coverage.method_coverage,
                "class_coverage": regression_coverage.class_coverage,
            },
            "diff": {
                "line_coverage": regression_coverage.line_coverage
                - baseline_coverage.line_coverage,
                "branch_coverage": regression_coverage.branch_coverage
                - baseline_coverage.branch_coverage,
                "method_coverage": regression_coverage.method_coverage
                - baseline_coverage.method_coverage,
                "class_coverage": regression_coverage.class_coverage
                - baseline_coverage.class_coverage,
            },
        }

    def get_regression_details(self, comparison: TestComparison) -> list[dict[str, Any]]:
        """获取回归问题详情.

        Args:
            comparison: 测试对比结果

        Returns:
            List[Dict[str, Any]]: 回归问题详情列表
        """
        details: list[dict[str, Any]] = []

        for diff in comparison.regression_issues:
            details.append(
                {
                    "test_name": diff.full_name,
                    "baseline_status": diff.baseline_status.value if diff.baseline_status else None,
                    "regression_status": diff.regression_status.value
                    if diff.regression_status
                    else None,
                    "diff_type": diff.diff_type.value,
                    "analysis_result": diff.analysis_result,
                    "analysis_reason": diff.analysis_reason,
                }
            )

        return details

    def _create_diff(
        self,
        baseline_result: TestResult | None,
        regression_result: TestResult,
        baseline: TestRun,
        regression: TestRun,
    ) -> TestDiff:
        """创建测试差异对象.

        Args:
            baseline_result: 基线测试结果
            regression_result: 回归测试结果
            baseline: 基线测试运行
            regression: 回归测试运行

        Returns:
            TestDiff: 测试差异对象
        """
        baseline_status = baseline_result.status if baseline_result else None
        regression_status = regression_result.status

        diff_type = self._determine_diff_type(baseline_status, regression_status)
        analysis_result, analysis_reason = self._analyze_diff(
            diff_type, baseline_status, regression_status
        )

        return TestDiff(
            baseline_run_id=baseline.id or 0,
            regression_run_id=regression.id or 0,
            test_class=regression_result.test_class,
            test_method=regression_result.test_method,
            baseline_status=baseline_status,
            regression_status=regression_status,
            diff_type=diff_type,
            analysis_result=analysis_result,
            analysis_reason=analysis_reason,
        )

    def _determine_diff_type(
        self, baseline_status: TestStatus | None, regression_status: TestStatus
    ) -> DiffType:
        """确定差异类型.

        Args:
            baseline_status: 基线测试状态
            regression_status: 回归测试状态

        Returns:
            DiffType: 差异类型
        """
        if baseline_status is None:
            # 新增测试
            if regression_status == TestStatus.PASSED:
                return DiffType.STABLE_PASS
            return DiffType.STABLE_FAIL

        if baseline_status == TestStatus.PASSED and regression_status == TestStatus.FAILED:
            return DiffType.NEW_FAIL

        if baseline_status == TestStatus.FAILED and regression_status == TestStatus.PASSED:
            return DiffType.NEW_PASS

        if baseline_status == TestStatus.PASSED and regression_status == TestStatus.PASSED:
            return DiffType.STABLE_PASS

        return DiffType.STABLE_FAIL

    def _analyze_diff(
        self,
        diff_type: DiffType,
        baseline_status: TestStatus | None,
        regression_status: TestStatus,
    ) -> tuple[str, str | None]:
        """分析差异.

        Args:
            diff_type: 差异类型
            baseline_status: 基线测试状态
            regression_status: 回归测试状态

        Returns:
            Tuple[str, Optional[str]]: (分析结果, 分析原因)
        """

        def _status_value(status: TestStatus | None) -> str:
            return status.value if status is not None else "UNKNOWN"

        if diff_type == DiffType.NEW_FAIL:
            return (
                "UNEXPECTED",
                "Test regressed from "
                f"{_status_value(baseline_status)} to {regression_status.value}",
            )

        if diff_type == DiffType.NEW_PASS:
            return (
                "EXPECTED",
                f"Test improved from {_status_value(baseline_status)} to {regression_status.value}",
            )

        if baseline_status is None:
            return ("EXPECTED", "New test added in regression run")

        return ("EXPECTED", "No significant change in test status")
