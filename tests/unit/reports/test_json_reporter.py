"""测试JSON报告生成器."""

import json
from pathlib import Path

from jcia.reports.base import ReportData
from jcia.reports.json_reporter import JSONReporter


class TestJSONReporter:
    """测试JSONReporter."""

    def test_init_default(self) -> None:
        """测试默认初始化."""
        reporter = JSONReporter()

        assert reporter.output_dir == Path.cwd()
        assert reporter._indent == 2

    def test_init_custom(self, tmp_path: Path) -> None:
        """测试自定义初始化."""
        reporter = JSONReporter(output_dir=tmp_path, indent=4)

        assert reporter.output_dir == tmp_path
        assert reporter._indent == 4

    def test_get_format(self) -> None:
        """测试获取格式."""
        reporter = JSONReporter()

        assert reporter.get_format() == "json"

    def test_generate_empty_data(self, tmp_path: Path) -> None:
        """测试生成空数据报告."""
        reporter = JSONReporter(output_dir=tmp_path)
        data = ReportData(title="空报告测试")

        result = reporter.generate(data)

        assert result.success is True
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.format == "json"
        assert result.size_bytes > 0

        # 验证JSON内容
        content = json.loads(result.content)
        assert content["title"] == "空报告测试"
        assert "timestamp" in content

    def test_generate_with_metadata(self, tmp_path: Path) -> None:
        """测试生成带元数据的报告."""
        reporter = JSONReporter(output_dir=tmp_path)
        data = ReportData(
            title="元数据测试",
            metadata={"version": "1.0", "author": "test"},
        )

        result = reporter.generate(data)

        assert result.success is True
        content = json.loads(result.content)
        assert content["metadata"]["version"] == "1.0"
        assert content["metadata"]["author"] == "test"

    def test_generate_to_string(self, tmp_path: Path) -> None:
        """测试生成字符串（不保存文件）."""
        reporter = JSONReporter(output_dir=tmp_path)
        data = ReportData(title="字符串测试")

        content_str = reporter.generate_to_string(data)

        assert isinstance(content_str, str)
        content = json.loads(content_str)
        assert content["title"] == "字符串测试"

    def test_generate_creates_directory(self, tmp_path: Path) -> None:
        """测试生成报告时创建目录."""
        new_dir = tmp_path / "new_json_reports"
        reporter = JSONReporter(output_dir=new_dir)
        data = ReportData()

        result = reporter.generate(data)

        assert result.success is True
        assert new_dir.exists()

    def test_generate_file_naming(self, tmp_path: Path) -> None:
        """测试生成文件命名."""
        reporter = JSONReporter(output_dir=tmp_path)
        data = ReportData()

        result = reporter.generate(data)

        assert result.output_path is not None
        assert result.output_path.name.startswith("test_report_")
        assert result.output_path.name.endswith(".json")

    def test_generate_indent(self, tmp_path: Path) -> None:
        """测试JSON缩进."""
        reporter = JSONReporter(output_dir=tmp_path, indent=4)
        data = ReportData(title="缩进测试")

        result = reporter.generate(data)

        # 检查缩进（4空格）
        assert "    " in result.content

    def test_generate_with_invalid_path(self) -> None:
        """测试生成报告时路径无效."""
        # 使用一个无效的路径（Windows 保留名称）
        import platform

        if platform.system() == "Windows":
            invalid_path = Path("COM1")  # Windows 保留名称
        else:
            invalid_path = Path("/nonexistent_root_dir_xyz/report.json")

        reporter = JSONReporter(output_dir=invalid_path)
        data = ReportData(title="无效路径测试")

        result = reporter.generate(data)

        # 应该返回失败结果
        assert result.success is False
        assert result.error_message is not None
