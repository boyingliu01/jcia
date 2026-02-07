"""测试GenerateReportUseCase用例.

测试生成测试报告用例的功能，包括JSON、HTML、Markdown和控制台格式的报告生成。
"""

import json
from pathlib import Path

import pytest

from jcia.core.entities.change_set import ChangeSet, ChangeType, FileChange, MethodChange
from jcia.core.entities.impact_graph import ImpactGraph, ImpactNode, ImpactSeverity, ImpactType
from jcia.core.entities.test_run import CoverageData, RunStatus, RunType, TestRun, TestStatus
from jcia.core.use_cases.generate_report import (
    GenerateReportRequest,
    GenerateReportResponse,
    GenerateReportUseCase,
)


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """创建临时输出目录.

    Args:
        tmp_path: pytest临时目录

    Returns:
        Path: 临时输出目录路径
    """
    output_dir = tmp_path / "reports"
    output_dir.mkdir(parents=True)
    return output_dir


@pytest.fixture
def sample_test_run() -> TestRun:
    """创建示例测试运行对象.

    Returns:
        TestRun: 测试运行对象
    """
    coverage = CoverageData(
        line_coverage=85.5,
        branch_coverage=78.2,
        method_coverage=90.0,
        class_coverage=82.0,
        covered_lines=4250,
        total_lines=5000,
    )

    test_run = TestRun(
        id=1,
        commit_hash="abc123def456",
        run_type=RunType.REGRESSION,
        status=RunStatus.COMPLETED,
        total_tests=100,
        passed_tests=95,
        failed_tests=5,
        skipped_tests=0,
        total_duration_ms=120500,
        coverage=coverage,
    )
    # Manually set the test results to ensure proper count
    for _ in range(95):
        from jcia.core.entities.test_run import TestResult

        test_run.add_result(TestResult(status=TestStatus.PASSED))
    for _ in range(5):
        test_run.add_result(TestResult(status=TestStatus.FAILED))
    return test_run


@pytest.fixture
def sample_impact_graph() -> ImpactGraph:
    """创建示例影响图.

    Returns:
        ImpactGraph: 影响图对象
    """
    node = ImpactNode(
        method_name="com.example.Service.method",
        class_name="com.example.Service",
        impact_type=ImpactType.DIRECT,
        severity=ImpactSeverity.HIGH,
    )

    graph = ImpactGraph()
    graph.add_node(node)
    graph.root_methods = ["com.example.Service.method"]
    return graph


@pytest.fixture
def sample_change_set() -> ChangeSet:
    """创建示例变更集合.

    Returns:
        ChangeSet: 变更集合对象
    """
    method_change = MethodChange(
        class_name="com.example.Service",
        method_name="method",
        change_type=ChangeType.MODIFY,
    )

    file_change = FileChange(
        file_path="src/main/java/com/example/Service.java",
        change_type=ChangeType.MODIFY,
        method_changes=[method_change],
    )

    return ChangeSet(file_changes=[file_change])


class TestGenerateReportRequest:
    """测试GenerateReportRequest请求类."""

    def test_init_with_required_fields(self) -> None:
        """测试使用必填字段初始化请求."""
        output_dir = Path("/tmp/reports")

        request = GenerateReportRequest(output_dir=output_dir)

        assert request.output_dir == output_dir
        assert request.format == "json"
        assert request.test_run is None
        assert request.impact_graph is None
        assert request.change_set is None
        assert request.include_details is True
        assert request.include_charts is False

    def test_init_with_all_fields(self, temp_output_dir: Path, sample_test_run: TestRun) -> None:
        """测试使用所有字段初始化请求."""
        request = GenerateReportRequest(
            output_dir=temp_output_dir,
            format="html",
            test_run=sample_test_run,
            include_details=False,
            include_charts=True,
        )

        assert request.output_dir == temp_output_dir
        assert request.format == "html"
        assert request.test_run == sample_test_run
        assert request.include_details is False
        assert request.include_charts is True


class TestGenerateReportResponse:
    """测试GenerateReportResponse响应类."""

    def test_init(self) -> None:
        """测试初始化响应."""
        response = GenerateReportResponse(
            report_path=Path("/tmp/report.json"),
            format="json",
            content="{}",
            metadata={"size_bytes": 2},
        )

        assert response.report_path == Path("/tmp/report.json")
        assert response.format == "json"
        assert response.content == "{}"
        assert response.metadata == {"size_bytes": 2}

    def test_init_with_defaults(self) -> None:
        """测试使用默认值初始化响应."""
        response = GenerateReportResponse()

        assert response.report_path is None
        assert response.format == "json"
        assert response.content is None
        assert response.metadata == {}


class TestGenerateReportUseCase:
    """测试GenerateReportUseCase用例."""

    def test_init(self) -> None:
        """测试初始化用例."""
        use_case = GenerateReportUseCase()
        assert use_case is not None

    def test_validate_request_valid_directory(self, temp_output_dir: Path) -> None:
        """测试验证有效的输出目录."""
        request = GenerateReportRequest(output_dir=temp_output_dir, format="json")
        use_case = GenerateReportUseCase()

        use_case._validate_request(request)  # 不应抛出异常

    def test_validate_request_invalid_directory(self) -> None:
        """测试验证不存在的输出目录."""
        request = GenerateReportRequest(output_dir=Path("/nonexistent/directory"), format="json")
        use_case = GenerateReportUseCase()

        with pytest.raises(ValueError, match="输出目录不存在"):
            use_case._validate_request(request)

    def test_validate_request_valid_format(self, temp_output_dir: Path) -> None:
        """测试验证有效的报告格式."""
        valid_formats = ["json", "html", "markdown", "console"]

        for fmt in valid_formats:
            request = GenerateReportRequest(output_dir=temp_output_dir, format=fmt)
            use_case = GenerateReportUseCase()
            use_case._validate_request(request)  # 不应抛出异常

    def test_validate_request_invalid_format(self, temp_output_dir: Path) -> None:
        """测试验证无效的报告格式."""
        request = GenerateReportRequest(output_dir=temp_output_dir, format="pdf")
        use_case = GenerateReportUseCase()

        with pytest.raises(ValueError, match="不支持的格式"):
            use_case._validate_request(request)

    def test_prepare_report_data_with_test_run(
        self, temp_output_dir: Path, sample_test_run: TestRun
    ) -> None:
        """测试准备报告数据包含测试运行."""
        request = GenerateReportRequest(output_dir=temp_output_dir, test_run=sample_test_run)
        use_case = GenerateReportUseCase()

        report_data = use_case._prepare_report_data(request)

        assert "timestamp" in report_data
        assert report_data["test_run"] is not None
        assert report_data["test_run"]["commit_hash"] == "abc123def456"
        assert report_data["test_run"]["total_tests"] == 100
        assert report_data["test_run"]["passed_tests"] == 95
        assert report_data["test_run"]["failed_tests"] == 5

    def test_prepare_report_data_with_impact_graph(
        self, temp_output_dir: Path, sample_impact_graph: ImpactGraph
    ) -> None:
        """测试准备报告数据包含影响图."""
        request = GenerateReportRequest(
            output_dir=temp_output_dir, impact_graph=sample_impact_graph
        )
        use_case = GenerateReportUseCase()

        report_data = use_case._prepare_report_data(request)

        assert "timestamp" in report_data
        assert report_data["impact_graph"] is not None
        assert "nodes" in report_data["impact_graph"]

    def test_prepare_report_data_with_change_set(
        self, temp_output_dir: Path, sample_change_set: ChangeSet
    ) -> None:
        """测试准备报告数据包含变更集合."""
        request = GenerateReportRequest(output_dir=temp_output_dir, change_set=sample_change_set)
        use_case = GenerateReportUseCase()

        report_data = use_case._prepare_report_data(request)

        assert "timestamp" in report_data
        assert report_data["change_set"] is not None
        assert "changed_files" in report_data["change_set"]

    def test_prepare_report_data_empty(self, temp_output_dir: Path) -> None:
        """测试准备报告数据为空."""
        request = GenerateReportRequest(output_dir=temp_output_dir)
        use_case = GenerateReportUseCase()

        report_data = use_case._prepare_report_data(request)

        assert "timestamp" in report_data
        assert report_data["test_run"] is None
        assert report_data["impact_graph"] is None
        assert report_data["change_set"] is None

    def test_serialize_test_run(self, sample_test_run: TestRun) -> None:
        """测试序列化测试运行对象."""
        use_case = GenerateReportUseCase()
        serialized = use_case._serialize_test_run(sample_test_run)

        assert serialized["commit_hash"] == "abc123def456"
        assert serialized["run_type"] == "regression"
        assert serialized["status"] == "completed"
        assert serialized["total_tests"] == 100
        assert serialized["passed_tests"] == 95
        assert serialized["failed_tests"] == 5
        assert serialized["success_rate"] == 0.95
        assert serialized["coverage"] is not None
        assert serialized["coverage"]["line_coverage"] == 85.5
        assert serialized["coverage"]["branch_coverage"] == 78.2

    def test_serialize_test_run_without_coverage(self, temp_output_dir: Path) -> None:
        """测试序列化没有覆盖率的测试运行对象."""
        test_run = TestRun(
            id=1,
            commit_hash="abc123",
            run_type=RunType.REGRESSION,
            status=RunStatus.COMPLETED,
            total_tests=50,
            passed_tests=50,
            failed_tests=0,
        )

        use_case = GenerateReportUseCase()
        serialized = use_case._serialize_test_run(test_run)

        assert serialized["coverage"] is None

    def test_generate_json_report(self, temp_output_dir: Path, sample_test_run: TestRun) -> None:
        """测试生成JSON格式报告."""
        request = GenerateReportRequest(
            output_dir=temp_output_dir, format="json", test_run=sample_test_run
        )
        use_case = GenerateReportUseCase()

        response = use_case.execute(request)

        assert response.format == "json"
        assert response.report_path is not None
        assert response.report_path.exists()
        assert response.content is not None

        # 验证JSON内容
        data = json.loads(response.content)
        assert data["test_run"]["commit_hash"] == "abc123def456"

    def test_generate_html_report(self, temp_output_dir: Path, sample_test_run: TestRun) -> None:
        """测试生成HTML格式报告."""
        request = GenerateReportRequest(
            output_dir=temp_output_dir, format="html", test_run=sample_test_run
        )
        use_case = GenerateReportUseCase()

        response = use_case.execute(request)

        assert response.format == "html"
        assert response.report_path is not None
        assert response.report_path.exists()
        assert response.content is not None
        assert "<!DOCTYPE html>" in response.content
        assert "测试报告" in response.content

    def test_generate_markdown_report(
        self, temp_output_dir: Path, sample_test_run: TestRun
    ) -> None:
        """测试生成Markdown格式报告."""
        request = GenerateReportRequest(
            output_dir=temp_output_dir, format="markdown", test_run=sample_test_run
        )
        use_case = GenerateReportUseCase()

        response = use_case.execute(request)

        assert response.format == "markdown"
        assert response.report_path is not None
        assert response.report_path.exists()
        assert response.content is not None
        assert "# 测试报告" in response.content

    def test_generate_console_report(self, temp_output_dir: Path, sample_test_run: TestRun) -> None:
        """测试生成控制台格式报告."""
        request = GenerateReportRequest(
            output_dir=temp_output_dir, format="console", test_run=sample_test_run
        )
        use_case = GenerateReportUseCase()

        response = use_case.execute(request)

        assert response.format == "console"
        assert response.report_path is None  # Console格式不保存文件
        assert response.content is not None
        assert "测试报告" in response.content

    def test_create_html_template(self, sample_test_run: TestRun) -> None:
        """测试创建HTML模板."""
        use_case = GenerateReportUseCase()
        report_data = {
            "timestamp": "2024-01-01T12:00:00",
            "test_run": use_case._serialize_test_run(sample_test_run),
        }

        html = use_case._create_html_template(report_data, include_details=True)

        assert "<!DOCTYPE html>" in html
        assert "测试报告" in html
        assert "总测试数: 100" in html
        assert "通过测试数:" in html
        assert "95" in html
        assert "失败测试数:" in html
        assert "5" in html
        assert "覆盖率" in html

    def test_create_html_template_without_details(self, sample_test_run: TestRun) -> None:
        """测试创建HTML模板不包含详细信息."""
        use_case = GenerateReportUseCase()
        report_data = {
            "timestamp": "2024-01-01T12:00:00",
            "test_run": use_case._serialize_test_run(sample_test_run),
        }

        html = use_case._create_html_template(report_data, include_details=False)

        assert "<!DOCTYPE html>" in html
        assert "测试报告" in html
        assert "总测试数: 100" in html
        # 不应该显示覆盖率（因为include_details=False）
        assert "覆盖率" not in html

    def test_create_markdown_content(self, sample_test_run: TestRun) -> None:
        """测试创建Markdown内容."""
        use_case = GenerateReportUseCase()
        report_data = {
            "timestamp": "2024-01-01T12:00:00",
            "test_run": use_case._serialize_test_run(sample_test_run),
        }

        md = use_case._create_markdown_content(report_data, include_details=True)

        assert "# 测试报告" in md
        assert "总测试数: 100" in md
        assert "通过测试数: 95" in md
        assert "失败测试数: 5" in md
        assert "## 覆盖率" in md

    def test_create_markdown_content_without_details(self, sample_test_run: TestRun) -> None:
        """测试创建Markdown内容不包含详细信息."""
        use_case = GenerateReportUseCase()
        report_data = {
            "timestamp": "2024-01-01T12:00:00",
            "test_run": use_case._serialize_test_run(sample_test_run),
        }

        md = use_case._create_markdown_content(report_data, include_details=False)

        assert "# 测试报告" in md
        assert "总测试数: 100" in md
        # 不应该显示覆盖率
        assert "## 覆盖率" not in md

    def test_create_console_output(self, sample_test_run: TestRun) -> None:
        """测试创建控制台输出."""
        use_case = GenerateReportUseCase()
        report_data = {
            "timestamp": "2024-01-01T12:00:00",
            "test_run": use_case._serialize_test_run(sample_test_run),
        }

        output = use_case._create_console_output(report_data, include_details=True)

        assert "测试报告" in output
        assert "总测试数: 100" in output
        assert "通过测试数: 95" in output
        assert "失败测试数: 5" in output
        assert "覆盖率" in output

    def test_create_console_output_without_details(self, sample_test_run: TestRun) -> None:
        """测试创建控制台输出不包含详细信息."""
        use_case = GenerateReportUseCase()
        report_data = {
            "timestamp": "2024-01-01T12:00:00",
            "test_run": use_case._serialize_test_run(sample_test_run),
        }

        output = use_case._create_console_output(report_data, include_details=False)

        assert "测试报告" in output
        assert "总测试数: 100" in output
        # 不应该显示覆盖率
        assert "覆盖率" not in output

    def test_get_timestamp(self) -> None:
        """测试获取时间戳."""
        use_case = GenerateReportUseCase()
        timestamp = use_case._get_timestamp()

        assert isinstance(timestamp, str)
        assert len(timestamp) > 0
        # 验证ISO格式
        assert "T" in timestamp

    def test_execute_with_all_data(
        self,
        temp_output_dir: Path,
        sample_test_run: TestRun,
        sample_impact_graph: ImpactGraph,
        sample_change_set: ChangeSet,
    ) -> None:
        """测试执行用例包含所有数据."""
        request = GenerateReportRequest(
            output_dir=temp_output_dir,
            format="json",
            test_run=sample_test_run,
            impact_graph=sample_impact_graph,
            change_set=sample_change_set,
            include_details=True,
        )

        use_case = GenerateReportUseCase()
        response = use_case.execute(request)

        assert response.report_path is not None
        assert response.report_path.exists()
        assert response.content is not None

        data = json.loads(response.content)
        assert data["test_run"] is not None
        assert data["impact_graph"] is not None
        assert data["change_set"] is not None

    def test_execute_unsupported_format_raises_error(self, temp_output_dir: Path) -> None:
        """测试执行用例不支持的格式抛出异常."""
        request = GenerateReportRequest(output_dir=temp_output_dir, format="pdf")
        use_case = GenerateReportUseCase()

        with pytest.raises(ValueError, match="不支持的格式"):
            use_case.execute(request)
