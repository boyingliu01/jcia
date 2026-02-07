"""测试执行回归测试用例."""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from jcia.core.entities.test_run import (
    CoverageData,
    RunStatus,
    RunType,
    TestResult,
    TestRun,
    TestStatus,
)
from jcia.core.interfaces.test_runner import TestExecutionResult, TestSuiteResult
from jcia.core.use_cases.run_regression import (
    RunRegressionRequest,
    RunRegressionResponse,
    RunRegressionUseCase,
)


class TestRunRegressionRequest:
    """测试RunRegressionRequest."""

    def test_init_with_required_fields(self, tmp_path: Path) -> None:
        """测试使用必需字段初始化."""
        request = RunRegressionRequest(project_path=tmp_path, regression_commit="abc123")
        assert request.project_path == tmp_path
        assert request.test_cases is None
        assert request.baseline_commit is None
        assert request.regression_commit == "abc123"
        assert request.run_type == "regression"
        assert request.execute_coverage is False
        assert request.save_results is True

    def test_init_with_all_fields(self, tmp_path: Path) -> None:
        """测试使用所有字段初始化."""
        request = RunRegressionRequest(
            project_path=tmp_path,
            regression_commit="def456",
            baseline_commit="abc123",
            execute_coverage=True,
            save_results=False,
        )
        assert request.baseline_commit == "abc123"
        assert request.regression_commit == "def456"
        assert request.execute_coverage is True
        assert request.save_results is False


class TestRunRegressionResponse:
    """测试RunRegressionResponse."""

    def test_init(self) -> None:
        """测试初始化."""
        response = RunRegressionResponse(summary={"key": "value"})
        assert response.baseline_run is None
        assert response.regression_run is None
        assert response.comparison is None
        assert response.summary == {"key": "value"}


class TestRunRegressionUseCase:
    """测试RunRegressionUseCase."""

    @pytest.fixture
    def mock_test_executor(self) -> Mock:
        """创建模拟测试执行器."""
        executor = Mock()
        return executor

    @pytest.fixture
    def mock_repositories(self) -> tuple[Mock, Mock, Mock]:
        """创建模拟仓储."""
        test_run_repo = Mock()
        test_result_repo = Mock()
        test_diff_repo = Mock()
        return test_run_repo, test_result_repo, test_diff_repo

    @pytest.fixture
    def use_case(
        self, mock_test_executor: Mock, mock_repositories: tuple[Mock, Mock, Mock]
    ) -> RunRegressionUseCase:
        """创建用例实例."""
        test_run_repo, test_result_repo, test_diff_repo = mock_repositories
        return RunRegressionUseCase(
            test_executor=mock_test_executor,
            test_run_repo=test_run_repo,
            test_result_repo=test_result_repo,
            test_diff_repo=test_diff_repo,
        )

    @pytest.fixture
    def valid_project_path(self, tmp_path: Path) -> Path:
        """创建有效的项目路径."""
        return tmp_path

    def test_init_with_executor(self, mock_test_executor: Mock) -> None:
        """测试使用执行器初始化用例."""
        use_case = RunRegressionUseCase(test_executor=mock_test_executor)
        assert use_case._executor is not None
        assert use_case._comparison_service is not None

    def test_execute_regression_only(
        self, use_case: RunRegressionUseCase, valid_project_path: Path
    ) -> None:
        """测试仅执行回归测试."""
        # Arrange
        request = RunRegressionRequest(project_path=valid_project_path, regression_commit="abc123")

        # Mock test execution
        mock_suite_result = self._create_mock_suite_result()
        use_case._executor.execute_tests = Mock(return_value=mock_suite_result)

        # Act
        response = use_case.execute(request)

        # Assert
        assert isinstance(response, RunRegressionResponse)
        assert response.regression_run is not None
        assert response.summary["regression_commit"] == "abc123"

    def test_execute_full_regression(
        self, use_case: RunRegressionUseCase, valid_project_path: Path
    ) -> None:
        """测试执行完整的回归测试（基线+回归）."""
        # Arrange
        request = RunRegressionRequest(
            project_path=valid_project_path,
            baseline_commit="abc123",
            regression_commit="def456",
        )

        # Mock test execution
        mock_suite_result = self._create_mock_suite_result()
        use_case._executor.execute_tests = Mock(return_value=mock_suite_result)

        # Act
        response = use_case.execute(request)

        # Assert
        assert isinstance(response, RunRegressionResponse)
        assert response.baseline_run is not None
        assert response.regression_run is not None
        assert response.comparison is not None
        assert response.baseline_run.commit_hash == "abc123"
        assert response.regression_run.commit_hash == "def456"

    def test_execute_with_coverage(
        self, use_case: RunRegressionUseCase, valid_project_path: Path
    ) -> None:
        """测试执行回归测试并收集覆盖率."""
        # Arrange
        request = RunRegressionRequest(
            project_path=valid_project_path,
            regression_commit="abc123",
            execute_coverage=True,
        )

        # Mock test execution
        mock_suite_result = self._create_mock_suite_result()
        use_case._executor.execute_with_coverage = Mock(return_value=mock_suite_result)

        # Act
        response = use_case.execute(request)

        # Assert
        assert response.regression_run is not None
        assert response.regression_run.coverage is not None
        assert response.regression_run.coverage.line_coverage == 85.5

    def test_validate_request_invalid_path(self, use_case: RunRegressionUseCase) -> None:
        """测试验证请求：无效路径."""
        # Arrange
        request = RunRegressionRequest(
            project_path=Path("/nonexistent/path"), regression_commit="abc123"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="项目路径不存在"):
            use_case.execute(request)

    def test_validate_request_missing_parameters(
        self, use_case: RunRegressionUseCase, valid_project_path: Path
    ) -> None:
        """测试验证请求：缺少必要参数."""
        # Arrange
        request = RunRegressionRequest(project_path=valid_project_path)

        # Act & Assert
        with pytest.raises(ValueError, match="必须提供"):
            use_case.execute(request)

    def test_save_test_runs(
        self,
        use_case: RunRegressionUseCase,
        mock_repositories: tuple[Mock, Mock, Mock],
        valid_project_path: Path,
    ) -> None:
        """测试保存测试运行."""
        # Arrange
        test_run_repo, test_result_repo, test_diff_repo = mock_repositories

        request = RunRegressionRequest(
            project_path=valid_project_path,
            baseline_commit="abc123",
            regression_commit="def456",
            save_results=True,
        )

        use_case._executor.execute_tests = Mock(return_value=self._create_mock_suite_result())

        # Act
        use_case.execute(request)

        # Assert
        assert test_run_repo.save.call_count == 2
        assert test_result_repo.save_batch.call_count == 2
        assert test_diff_repo.save_batch.call_count == 1

    def test_generate_summary(self, use_case: RunRegressionUseCase) -> None:
        """测试生成摘要."""
        # Arrange
        baseline_run = self._create_mock_test_run(
            commit_hash="abc123", total=50, passed=45, failed=5
        )
        regression_run = self._create_mock_test_run(
            commit_hash="def456", total=50, passed=40, failed=10
        )

        # Create a mock comparison
        mock_comparison = MagicMock()
        mock_comparison.new_failures = [MagicMock()] * 5  # 5 new failures
        mock_comparison.new_passes = [MagicMock()] * 2  # 2 new passes
        mock_comparison.has_regression_issues = True

        # Act
        summary = use_case._generate_summary(baseline_run, regression_run, mock_comparison)

        # Assert
        assert summary["baseline_commit"] == "abc123"
        assert summary["regression_commit"] == "def456"
        assert summary["baseline_tests"] == 50
        assert summary["regression_tests"] == 50
        assert summary["new_failures"] == 5
        assert summary["new_passes"] == 2
        assert summary["has_regression_issues"] is True

    def test_generate_summary_without_comparison(self, use_case: RunRegressionUseCase) -> None:
        """测试生成摘要不包含对比."""
        # Arrange
        baseline_run = self._create_mock_test_run(commit_hash="abc123")
        regression_run = self._create_mock_test_run(commit_hash="def456")

        # Act
        summary = use_case._generate_summary(baseline_run, regression_run, None)

        # Assert
        assert summary["baseline_commit"] == "abc123"
        assert summary["regression_commit"] == "def456"
        assert "new_failures" not in summary
        assert "new_passes" not in summary

    def test_generate_regression_only_summary(self, use_case: RunRegressionUseCase) -> None:
        """测试生成仅回归测试摘要."""
        # Arrange
        regression_run = self._create_mock_test_run(
            commit_hash="abc123", total=100, passed=95, failed=5
        )

        # Act
        summary = use_case._generate_regression_only_summary(regression_run)

        # Assert
        assert summary["regression_commit"] == "abc123"
        assert summary["total_tests"] == 100
        assert summary["passed_tests"] == 95
        assert summary["failed_tests"] == 5
        assert summary["success_rate"] == 0.95
        assert summary["has_failures"] is True

    def test_execute_tests_creates_test_run_with_results(
        self, use_case: RunRegressionUseCase, valid_project_path: Path
    ) -> None:
        """测试执行测试创建带有结果的测试运行."""
        # Arrange
        request = RunRegressionRequest(
            project_path=valid_project_path,
            regression_commit="abc123",
        )

        # Create mock suite result with test results
        mock_test_results = [
            TestExecutionResult(
                test_class="com.example.TestClass",
                test_method="testMethod1",
                status=TestStatus.PASSED,
                duration_ms=100,
            ),
            TestExecutionResult(
                test_class="com.example.TestClass",
                test_method="testMethod2",
                status=TestStatus.FAILED,
                duration_ms=200,
                error_message="AssertionError",
                stack_trace="Traceback...",
            ),
        ]

        mock_suite_result = TestSuiteResult(
            total_tests=2,
            passed_tests=1,
            failed_tests=1,
            skipped_tests=0,
            error_tests=0,
            total_duration_ms=300,
            coverage_percent=85.5,
            test_results=mock_test_results,
        )

        use_case._executor.execute_tests = Mock(return_value=mock_suite_result)

        # Act
        response = use_case.execute(request)

        # Assert
        assert response.regression_run is not None
        assert response.regression_run.total_tests == 2
        assert response.regression_run.passed_tests == 1
        assert response.regression_run.failed_tests == 1
        assert len(response.regression_run.test_results) == 2

    def _create_mock_suite_result(self) -> TestSuiteResult:
        """创建模拟测试套件结果."""
        return TestSuiteResult(
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            skipped_tests=0,
            error_tests=0,
            total_duration_ms=5000,
            coverage_percent=85.5,
            test_results=[],
        )

    def _create_mock_test_run(
        self, commit_hash: str, total: int = 10, passed: int = 8, failed: int = 2
    ) -> TestRun:
        """创建模拟测试运行."""
        coverage = CoverageData(
            line_coverage=85.5,
            branch_coverage=78.0,
            method_coverage=90.0,
            class_coverage=82.0,
        )

        test_run = TestRun(
            id=1,
            commit_hash=commit_hash,
            run_type=RunType.REGRESSION,
            status=RunStatus.COMPLETED,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            coverage=coverage,
        )

        # Add test results
        for _ in range(passed):
            test_run.add_result(TestResult(status=TestStatus.PASSED))
        for _ in range(failed):
            test_run.add_result(TestResult(status=TestStatus.FAILED))

        return test_run
