"""测试报告生成器基类和数据结构."""

from datetime import datetime
from pathlib import Path

from jcia.reports.base import BaseReporter, ReportData, ReportResult


class TestReportData:
    """测试ReportData数据类."""

    def test_init_default(self) -> None:
        """测试默认初始化."""
        data = ReportData()

        assert data.title == "测试报告"
        assert isinstance(data.timestamp, datetime)
        assert data.test_run is None
        assert data.baseline_run is None
        assert data.comparison is None
        assert data.impact_graph is None
        assert data.change_set is None
        assert data.metadata == {}

    def test_init_with_title(self) -> None:
        """测试带标题初始化."""
        data = ReportData(title="自定义报告")

        assert data.title == "自定义报告"

    def test_init_with_metadata(self) -> None:
        """测试带元数据初始化."""
        data = ReportData(metadata={"version": "1.0", "author": "test"})

        assert data.metadata == {"version": "1.0", "author": "test"}

    def test_to_dict_empty(self) -> None:
        """测试空数据转换为字典."""
        data = ReportData(title="测试")
        result = data.to_dict()

        assert result["title"] == "测试"
        assert "timestamp" in result
        assert result["metadata"] == {}
        assert "test_run" not in result
        assert "impact_graph" not in result


class TestReportResult:
    """测试ReportResult数据类."""

    def test_init_default(self) -> None:
        """测试默认初始化."""
        result = ReportResult()

        assert result.success is True
        assert result.output_path is None
        assert result.content == ""
        assert result.format == "unknown"
        assert result.size_bytes == 0
        assert result.error_message is None

    def test_init_success(self, tmp_path: Path) -> None:
        """测试成功结果初始化."""
        output_path = tmp_path / "report.json"
        result = ReportResult(
            success=True,
            output_path=output_path,
            content='{"test": "data"}',
            format="json",
            size_bytes=16,
        )

        assert result.success is True
        assert result.output_path == output_path
        assert result.content == '{"test": "data"}'
        assert result.format == "json"
        assert result.size_bytes == 16

    def test_init_failure(self) -> None:
        """测试失败结果初始化."""
        result = ReportResult(
            success=False,
            format="json",
            error_message="文件写入失败",
        )

        assert result.success is False
        assert result.error_message == "文件写入失败"


class ConcreteReporter(BaseReporter):
    """用于测试的具体报告生成器."""

    def generate(self, data: ReportData) -> ReportResult:
        """生成报告."""
        return ReportResult(
            success=True,
            content="test content",
            format=self.get_format(),
        )

    def get_format(self) -> str:
        """获取格式."""
        return "test"


class TestBaseReporter:
    """测试BaseReporter基类."""

    def test_init_default_output_dir(self) -> None:
        """测试默认输出目录."""
        reporter = ConcreteReporter()

        assert reporter.output_dir == Path.cwd()

    def test_init_custom_output_dir(self, tmp_path: Path) -> None:
        """测试自定义输出目录."""
        reporter = ConcreteReporter(output_dir=tmp_path)

        assert reporter.output_dir == tmp_path

    def test_set_output_dir(self, tmp_path: Path) -> None:
        """测试设置输出目录."""
        reporter = ConcreteReporter()
        reporter.output_dir = tmp_path

        assert reporter.output_dir == tmp_path

    def test_get_output_filename(self) -> None:
        """测试生成输出文件名."""
        reporter = ConcreteReporter()
        filename = reporter._get_output_filename("json")

        assert filename.startswith("test_report_")
        assert filename.endswith(".json")

    def test_ensure_output_dir_exists(self, tmp_path: Path) -> None:
        """测试确保输出目录存在（已存在）."""
        reporter = ConcreteReporter(output_dir=tmp_path)
        reporter._ensure_output_dir()

        assert tmp_path.exists()

    def test_ensure_output_dir_creates(self, tmp_path: Path) -> None:
        """测试确保输出目录存在（需创建）."""
        new_dir = tmp_path / "new_reports"
        reporter = ConcreteReporter(output_dir=new_dir)
        reporter._ensure_output_dir()

        assert new_dir.exists()

    def test_format_percentage(self) -> None:
        """测试格式化百分比."""
        reporter = ConcreteReporter()

        assert reporter._format_percentage(85.5) == "85.50%"
        assert reporter._format_percentage(100.0) == "100.00%"
        assert reporter._format_percentage(0.0) == "0.00%"

    def test_format_success_rate(self) -> None:
        """测试格式化成功率."""
        reporter = ConcreteReporter()

        assert reporter._format_success_rate(0.95) == "95.00%"
        assert reporter._format_success_rate(1.0) == "100.00%"
        assert reporter._format_success_rate(0.0) == "0.00%"

    def test_generate(self) -> None:
        """测试生成报告."""
        reporter = ConcreteReporter()
        data = ReportData()
        result = reporter.generate(data)

        assert result.success is True
        assert result.content == "test content"
        assert result.format == "test"

    def test_get_format(self) -> None:
        """测试获取格式."""
        reporter = ConcreteReporter()

        assert reporter.get_format() == "test"
