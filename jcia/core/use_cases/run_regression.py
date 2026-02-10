"""执行回归测试用例.

负责执行基线测试和回归测试，并比较结果。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jcia.core.entities.test_case import TestCase
    from jcia.core.entities.test_run import TestRun
    from jcia.core.interfaces.repository import (
        TestDiffRepository,
        TestResultRepository,
        TestRunRepository,
    )
    from jcia.core.interfaces.test_runner import TestExecutor


@dataclass
class RunRegressionRequest:
    """执行回归测试请求.

    Attributes:
        project_path: 项目路径
        test_cases: 要执行的测试用例（None则执行所有）
        baseline_commit: 基线提交哈希（可选）
        regression_commit: 回归提交哈希（可选）
        run_type: 运行类型
        execute_coverage: 是否收集覆盖率
        save_results: 是否保存结果到数据库
    """

    project_path: Path
    test_cases: list["TestCase"] | None = None
    baseline_commit: str | None = None
    regression_commit: str | None = None
    run_type: str = "regression"
    execute_coverage: bool = False
    save_results: bool = True


@dataclass
class RunRegressionResponse:
    """执行回归测试响应.

    Attributes:
        baseline_run: 基线测试运行
        regression_run: 回归测试运行
        comparison: 测试对比结果
        summary: 摘要信息
        metadata: 额外元数据
    """

    baseline_run: TestRun | None = None
    regression_run: TestRun | None = None
    comparison: Any | None = None
    summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class RunRegressionUseCase:
    """执行回归测试用例.

    协调测试执行、结果保存和比较分析。

    流程：
        1. 验证请求参数
        2. 根据请求类型执行测试
           - 仅执行回归测试
           - 同时执行基线和回归测试
        3. 保存测试结果
        4. 比较测试结果
        5. 生成响应
    """

    def __init__(
        self,
        test_executor: "TestExecutor",
        test_run_repo: "TestRunRepository | None" = None,
        test_result_repo: "TestResultRepository | None" = None,
        test_diff_repo: "TestDiffRepository | None" = None,
    ) -> None:
        """初始化用例.

        Args:
            test_executor: 测试执行器
            test_run_repo: 测试运行仓储
            test_result_repo: 测试结果仓储
            test_diff_repo: 测试差异仓储
        """
        # 导入服务避免循环依赖
        from jcia.core.services.change_comparison_service import ChangeComparisonService

        self._executor = test_executor
        self._test_run_repo = test_run_repo
        self._test_result_repo = test_result_repo
        self._test_diff_repo = test_diff_repo
        self._comparison_service = ChangeComparisonService()

    def execute(self, request: RunRegressionRequest) -> RunRegressionResponse:
        """执行回归测试用例.

        Args:
            request: 回归测试请求

        Returns:
            RunRegressionResponse: 测试响应

        Raises:
            ValueError: 请求参数无效
            Exception: 执行过程中发生错误
        """
        # 验证请求
        self._validate_request(request)

        # 根据请求类型执行测试
        if request.baseline_commit:
            # 执行基线和回归测试
            response = self._execute_full_regression(request)
        else:
            # 仅执行回归测试
            response = self._execute_regression_only(request)

        return response

    def _validate_request(self, request: RunRegressionRequest) -> None:
        """验证请求参数.

        Args:
            request: 回归测试请求

        Raises:
            ValueError: 请求参数无效
        """
        if not request.project_path.exists():
            msg = f"项目路径不存在: {request.project_path}"
            raise ValueError(msg)

        if not request.baseline_commit and not request.regression_commit:
            msg = "必须提供baseline_commit或regression_commit"
            raise ValueError(msg)

    def _execute_full_regression(self, request: RunRegressionRequest) -> RunRegressionResponse:
        """执行完整的回归测试（基线 + 回归）.

        Args:
            request: 回归测试请求

        Returns:
            RunRegressionResponse: 测试响应
        """
        # 执行基线测试
        baseline_run = self._execute_tests(
            request=request,
            commit=request.baseline_commit or "",
            run_type="baseline",
        )

        # 执行回归测试
        regression_run = self._execute_tests(
            request=request,
            commit=request.regression_commit or "",
            run_type="regression",
        )

        # 保存结果
        if request.save_results:
            self._save_test_runs(baseline_run, regression_run)

        # 比较结果
        comparison = self._comparison_service.compare(baseline_run, regression_run)

        # 生成摘要
        summary = self._generate_summary(baseline_run, regression_run, comparison)

        return RunRegressionResponse(
            baseline_run=baseline_run,
            regression_run=regression_run,
            comparison=comparison,
            summary=summary,
        )

    def _execute_regression_only(self, request: RunRegressionRequest) -> RunRegressionResponse:
        """仅执行回归测试.

        Args:
            request: 回归测试请求

        Returns:
            RunRegressionResponse: 测试响应
        """
        # 执行回归测试
        regression_run = self._execute_tests(
            request=request,
            commit=request.regression_commit or "",
            run_type="regression",
        )

        # 保存结果
        if request.save_results and self._test_run_repo:
            self._test_run_repo.save(regression_run)

        # 生成摘要
        summary = self._generate_regression_only_summary(regression_run)

        return RunRegressionResponse(
            regression_run=regression_run,
            summary=summary,
        )

    def _execute_tests(
        self, request: RunRegressionRequest, commit: str, run_type: str
    ) -> "TestRun":
        """执行测试.

        Args:
            request: 回归测试请求
            commit: 提交哈希
            run_type: 运行类型

        Returns:
            TestRun: 测试运行对象
        """
        # 导入实体避免循环依赖
        from jcia.core.entities.test_run import (
            CoverageData,
            RunStatus,
            RunType,
            TestResult,
            TestRun,
            TestStatus,
        )
        from jcia.core.interfaces.test_runner import (  # noqa: TCH001
            TestSuiteResult,
        )

        # 执行测试
        if request.execute_coverage:
            suite_result: TestSuiteResult = self._executor.execute_with_coverage(
                test_cases=request.test_cases,
                project_path=request.project_path,
            )
        else:
            suite_result = self._executor.execute_tests(
                test_cases=request.test_cases,
                project_path=request.project_path,
            )

        # 创建测试运行对象
        coverage_data = CoverageData(
            line_coverage=suite_result.coverage_percent,
            branch_coverage=0.0,
            method_coverage=0.0,
            class_coverage=0.0,
        )

        test_run = TestRun(
            commit_hash=commit,
            run_type=RunType.BASELINE if run_type == "baseline" else RunType.REGRESSION,
            status=RunStatus.COMPLETED,
            coverage=coverage_data,
        )

        # 添加测试结果
        for result in suite_result.test_results:
            test_result = TestResult(
                test_class=result.test_class,
                test_method=result.test_method,
                status=TestStatus.PASSED if result.status.value == "passed" else TestStatus.FAILED,
                duration_ms=result.duration_ms,
                error_message=result.error_message,
                stack_trace=result.stack_trace,
            )
            test_run.add_result(test_result)

        return test_run

    def _save_test_runs(
        self, baseline_run: "TestRun | None", regression_run: "TestRun | None"
    ) -> None:
        """保存测试运行结果.

        Args:
            baseline_run: 基线测试运行
            regression_run: 回归测试运行
        """
        if baseline_run and self._test_run_repo and self._test_result_repo:
            # 保存基线运行
            self._test_run_repo.save(baseline_run)
            self._test_result_repo.save_batch(baseline_run.test_results)

        if regression_run and self._test_run_repo and self._test_result_repo:
            # 保存回归运行
            self._test_run_repo.save(regression_run)
            self._test_result_repo.save_batch(regression_run.test_results)

            # 保存测试差异
            if baseline_run and self._test_diff_repo:
                comparison = self._comparison_service.compare(baseline_run, regression_run)
                self._test_diff_repo.save_batch(comparison.diffs)

    def _generate_summary(
        self,
        baseline_run: TestRun | None,
        regression_run: TestRun | None,
        comparison: Any,
    ) -> dict[str, Any]:
        """生成摘要.

        Args:
            baseline_run: 基线测试运行
            regression_run: 回归测试运行
            comparison: 测试对比结果

        Returns:
            dict: 摘要信息
        """
        summary = {
            "baseline_commit": baseline_run.commit_hash if baseline_run else None,
            "regression_commit": regression_run.commit_hash if regression_run else None,
            "baseline_tests": baseline_run.total_tests if baseline_run else 0,
            "regression_tests": regression_run.total_tests if regression_run else 0,
        }

        if comparison:
            summary["new_failures"] = len(comparison.new_failures)
            summary["new_passes"] = len(comparison.new_passes)
            summary["has_regression_issues"] = comparison.has_regression_issues

        return summary

    def _generate_regression_only_summary(self, regression_run: TestRun) -> dict[str, Any]:
        """生成仅回归测试摘要.

        Args:
            regression_run: 回归测试运行

        Returns:
            dict: 摘要信息
        """
        return {
            "regression_commit": regression_run.commit_hash,
            "total_tests": regression_run.total_tests,
            "passed_tests": regression_run.passed_tests,
            "failed_tests": regression_run.failed_tests,
            "success_rate": regression_run.success_rate,
            "has_failures": regression_run.has_failures,
        }
