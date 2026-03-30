"""测试HTML报告生成器."""

from pathlib import Path

from jcia.reports.base import ReportData
from jcia.reports.html_reporter import HTMLReporter


class TestHTMLReporter:
    """测试HTMLReporter."""

    def test_init_default(self) -> None:
        """测试默认初始化."""
        reporter = HTMLReporter()

        assert reporter.output_dir == Path.cwd()
        assert reporter._include_charts is True
        assert reporter._template_path is None

    def test_init_custom(self, tmp_path: Path) -> None:
        """测试自定义初始化."""
        reporter = HTMLReporter(
            output_dir=tmp_path,
            include_charts=False,
        )

        assert reporter.output_dir == tmp_path
        assert reporter._include_charts is False

    def test_get_format(self) -> None:
        """测试获取格式."""
        reporter = HTMLReporter()

        assert reporter.get_format() == "html"

    def test_generate_empty_data(self, tmp_path: Path) -> None:
        """测试生成空数据报告."""
        reporter = HTMLReporter(output_dir=tmp_path)
        data = ReportData(title="空报告测试")

        result = reporter.generate(data)

        assert result.success is True
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.format == "html"
        assert result.size_bytes > 0

        # 验证HTML内容
        assert "<!DOCTYPE html>" in result.content
        assert "<html" in result.content
        assert data.title in result.content

    def test_generate_with_metadata(self, tmp_path: Path) -> None:
        """测试生成带元数据的报告."""
        reporter = HTMLReporter(output_dir=tmp_path)
        data = ReportData(
            title="元数据测试",
            metadata={"version": "1.0", "author": "test"},
        )

        result = reporter.generate(data)

        assert result.success is True
        assert data.title in result.content

    def test_generate_creates_directory(self, tmp_path: Path) -> None:
        """测试生成报告时创建目录."""
        new_dir = tmp_path / "new_html_reports"
        reporter = HTMLReporter(output_dir=new_dir)
        data = ReportData()

        result = reporter.generate(data)

        assert result.success is True
        assert new_dir.exists()

    def test_generate_file_naming(self, tmp_path: Path) -> None:
        """测试生成文件命名."""
        reporter = HTMLReporter(output_dir=tmp_path)
        data = ReportData()

        result = reporter.generate(data)

        assert result.output_path is not None
        assert result.output_path.name.startswith("test_report_")
        assert result.output_path.name.endswith(".html")

    def test_render_html_structure(self, tmp_path: Path) -> None:
        """测试HTML结构."""
        reporter = HTMLReporter(output_dir=tmp_path)
        data = ReportData(title="结构测试")

        result = reporter.generate(data)

        # 预期的HTML标签
        expected_tags = [
            "<!DOCTYPE html>",
            "<html",
            "<head>",
            "<body>",
            "</body>",
            "</html>",
            "<title>",
            "<style>",
        ]

        for tag in expected_tags:
            assert tag in result.content

    def test_render_test_summary(self, tmp_path: Path) -> None:
        """测试渲染测试摘要."""
        reporter = HTMLReporter(output_dir=tmp_path)

        from jcia.core.entities.test_run import (
            CoverageData,
            RunStatus,
            RunType,
            TestResult,
            TestRun,
            TestStatus,
        )

        coverage = CoverageData(
            line_coverage=85.5,
            branch_coverage=78.0,
            method_coverage=90.0,
            class_coverage=82.0,
        )

        test_run = TestRun(
            id=1,
            commit_hash="abc123",
            run_type=RunType.REGRESSION,
            status=RunStatus.COMPLETED,
            total_tests=100,
            passed_tests=95,
            failed_tests=5,
            coverage=coverage,
        )

        # 添加测试结果
        for _ in range(95):
            test_run.add_result(TestResult(status=TestStatus.PASSED))
        for _ in range(5):
            test_run.add_result(TestResult(status=TestStatus.FAILED))

        data = ReportData(title="测试摘要测试", test_run=test_run)

        result = reporter.generate(data)

        # 验证测试摘要内容
        assert "测试摘要" in result.content
        assert "总测试数" in result.content
        assert "100" in result.content
        assert "95" in result.content
        assert "5" in result.content

    def test_render_comparison(self, tmp_path: Path) -> None:
        """测试渲染对比."""
        reporter = HTMLReporter(output_dir=tmp_path)

        from jcia.core.entities.test_run import (
            TestComparison,
            TestDiff,
            TestStatus,
        )

        # 创建对比数据
        diff = TestDiff(
            test_class="com.example.TestClass",
            test_method="testMethod",
            baseline_status=TestStatus.PASSED,
            regression_status=TestStatus.FAILED,
        )

        comparison = TestComparison(diffs=[diff])

        data = ReportData(title="对比测试", comparison=comparison)

        result = reporter.generate(data)

        # 验证对比内容
        assert "测试对比" in result.content
        assert "总差异数" in result.content
        assert "1" in result.content

    def test_render_impact_graph(self, tmp_path: Path) -> None:
        """测试渲染影响图."""
        reporter = HTMLReporter(output_dir=tmp_path)

        from jcia.core.entities.impact_graph import (
            ImpactGraph,
            ImpactNode,
            ImpactSeverity,
            ImpactType,
        )

        # 创建影响图
        node = ImpactNode(
            method_name="com.example.Service.method",
            class_name="com.example.Service",
            impact_type=ImpactType.DIRECT,
            severity=ImpactSeverity.HIGH,
        )

        graph = ImpactGraph()
        graph.add_node(node)

        data = ReportData(title="影响图测试", impact_graph=graph)

        result = reporter.generate(data)

        # 验证影响图内容
        assert "影响分析" in result.content
        assert "受影响方法" in result.content
        assert "com.example.Service.method" in result.content

    def test_render_change_set(self, tmp_path: Path) -> None:
        """测试渲染变更集."""
        reporter = HTMLReporter(output_dir=tmp_path)

        from jcia.core.entities.change_set import (
            ChangeSet,
            ChangeType,
            FileChange,
        )

        # 创建变更集
        file_change = FileChange(
            file_path="src/main/java/com/example/Service.java",
            change_type=ChangeType.MODIFY,
            insertions=10,
            deletions=5,
        )

        change_set = ChangeSet(file_changes=[file_change])

        data = ReportData(title="变更集测试", change_set=change_set)

        result = reporter.generate(data)

        # 验证变更集内容
        assert "代码变更" in result.content
        assert "变更文件" in result.content
        assert "Service.java" in result.content

    def test_include_charts_flag(self, tmp_path: Path) -> None:
        """测试包含图表标志."""
        reporter = HTMLReporter(output_dir=tmp_path, include_charts=True)
        data = ReportData()

        result = reporter.generate(data)

        assert result.success is True
        assert reporter._include_charts is True

    def test_generate_with_invalid_path(self) -> None:
        """测试生成报告时路径无效."""
        import platform

        if platform.system() == "Windows":
            invalid_path = Path("COM1")  # Windows 保留名称
        else:
            invalid_path = Path("/nonexistent_root_dir_xyz/report.html")

        reporter = HTMLReporter(output_dir=invalid_path)
        data = ReportData(title="无效路径测试")

        result = reporter.generate(data)

        # 应该返回失败结果
        assert result.success is False
        assert result.error_message is not None
