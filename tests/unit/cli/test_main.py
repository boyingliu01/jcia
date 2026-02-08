"""测试CLI命令行工具."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from jcia.cli.main import cli


class TestCLI:
    """测试CLI."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """创建Click CLI运行器."""
        return CliRunner()

    def test_cli_version(self, runner: CliRunner) -> None:
        """测试版本信息."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help(self, runner: CliRunner) -> None:
        """测试帮助信息."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "JCIA - Java Code Impact Analyzer" in result.output

    def test_analyze_command_help(self, runner: CliRunner) -> None:
        """测试analyze命令帮助."""
        result = runner.invoke(cli, ["analyze", "--help"])

        assert result.exit_code == 0
        assert "分析变更影响范围" in result.output

    def test_analyze_command_required_repo_path(self, runner: CliRunner) -> None:
        """测试analyze命令缺少必填参数."""
        result = runner.invoke(cli, ["analyze"])

        assert result.exit_code != 0
        assert "--repo-path" in result.output

    def test_analyze_command_basic(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试analyze命令基本执行."""
        # Create a mock git repository
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (git_dir / "refs" / "heads").mkdir(parents=True)

        result = runner.invoke(
            cli, ["analyze", "--repo-path", str(tmp_path), "--from-commit", "abc123"]
        )

        # Will fail because abc123 doesn't exist, but should show analysis UI
        assert "分析变更影响范围" in result.output
        assert str(tmp_path) in result.output

    def test_analyze_command_with_commit_range(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试analyze命令使用提交范围."""
        # Create a mock git repository
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (git_dir / "refs" / "heads").mkdir(parents=True)

        result = runner.invoke(
            cli,
            ["analyze", "--repo-path", str(tmp_path), "--commit-range", "abc123..def456"],
        )

        # Will fail because commits don't exist, but should show range
        assert "abc123..def456" in result.output

    def test_analyze_command_with_from_to_commit(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试analyze命令使用from/to提交."""
        # Create a mock git repository
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (git_dir / "refs" / "heads").mkdir(parents=True)

        result = runner.invoke(
            cli,
            [
                "analyze",
                "--repo-path",
                str(tmp_path),
                "--from-commit",
                "abc123",
                "--to-commit",
                "def456",
            ],
        )

        # Will fail because commit doesn't exist, but should show commit info
        assert "abc123" in result.output
        assert "def456" in result.output

    def test_analyze_command_with_max_depth(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试analyze命令使用最大深度."""
        # Create a mock git repository
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (git_dir / "refs" / "heads").mkdir(parents=True)

        result = runner.invoke(
            cli,
            [
                "analyze",
                "--repo-path",
                str(tmp_path),
                "--from-commit",
                "abc123",
                "--max-depth",
                "20",
            ],
        )

        # Will fail because commit doesn't exist, but should show depth
        assert "20" in result.output

    def test_test_command_help(self, runner: CliRunner) -> None:
        """测试test命令帮助."""
        result = runner.invoke(cli, ["test", "--help"])

        assert result.exit_code == 0
        assert "生成和运行测试用例" in result.output

    def test_test_command_required_repo_path(self, runner: CliRunner) -> None:
        """测试test命令缺少必填参数."""
        result = runner.invoke(cli, ["test"])

        assert result.exit_code != 0
        assert "--repo-path" in result.output

    def test_test_command_basic(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试test命令基本执行."""
        result = runner.invoke(cli, ["test", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0
        assert str(tmp_path) in result.output
        assert "当前使用Mock模式生成测试用例" in result.output

    def test_test_command_with_target_class(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试test命令使用目标类."""
        result = runner.invoke(
            cli,
            ["test", "--repo-path", str(tmp_path), "--target-class", "com.example.Service"],
        )

        assert result.exit_code == 0
        assert "com.example.Service" in result.output

    def test_test_command_with_coverage_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试test命令使用覆盖率文件."""
        coverage_file = tmp_path / "coverage.xml"
        coverage_file.write_text("<coverage></coverage>")

        result = runner.invoke(
            cli,
            ["test", "--repo-path", str(tmp_path), "--coverage-file", str(coverage_file)],
        )

        assert result.exit_code == 0
        assert "coverage.xml" in result.output

    def test_test_command_with_min_confidence(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试test命令使用最低置信度."""
        result = runner.invoke(
            cli,
            ["test", "--repo-path", str(tmp_path), "--min-confidence", "0.8"],
        )

        assert result.exit_code == 0
        assert "0.8" in result.output

    def test_report_command_help(self, runner: CliRunner) -> None:
        """测试report命令帮助."""
        result = runner.invoke(cli, ["report", "--help"])

        assert result.exit_code == 0
        assert "生成测试报告" in result.output

    def test_report_command_required_output_dir(self, runner: CliRunner) -> None:
        """测试report命令缺少必填参数."""
        result = runner.invoke(cli, ["report"])

        assert result.exit_code != 0
        assert "--output-dir" in result.output

    def test_report_command_basic(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试report命令基本执行."""
        output_dir = tmp_path / "reports"

        result = runner.invoke(cli, ["report", "--output-dir", str(output_dir)])

        assert result.exit_code == 0
        assert "生成测试报告" in result.output
        assert str(output_dir) in result.output

    def test_report_command_with_format_json(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试report命令使用JSON格式."""
        output_dir = tmp_path / "reports"

        result = runner.invoke(
            cli,
            ["report", "--output-dir", str(output_dir), "--format", "json"],
        )

        assert result.exit_code == 0
        assert "json" in result.output

    def test_report_command_with_format_html(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试report命令使用HTML格式."""
        output_dir = tmp_path / "reports"

        result = runner.invoke(
            cli,
            ["report", "--output-dir", str(output_dir), "--format", "html"],
        )

        assert result.exit_code == 0
        assert "html" in result.output

    def test_report_command_with_format_markdown(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试report命令使用Markdown格式."""
        output_dir = tmp_path / "reports"

        result = runner.invoke(
            cli,
            ["report", "--output-dir", str(output_dir), "--format", "markdown"],
        )

        assert result.exit_code == 0
        assert "markdown" in result.output

    def test_report_command_with_format_console(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试report命令使用控制台格式."""
        output_dir = tmp_path / "reports"

        result = runner.invoke(
            cli,
            ["report", "--output-dir", str(output_dir), "--format", "console"],
        )

        assert result.exit_code == 0
        assert "console" in result.output

    def test_report_command_with_include_details(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试report命令包含详细信息."""
        output_dir = tmp_path / "reports"

        result = runner.invoke(
            cli,
            ["report", "--output-dir", str(output_dir), "--include-details"],
        )

        assert result.exit_code == 0
        assert "包含详细信息" in result.output

    def test_config_command_help(self, runner: CliRunner) -> None:
        """测试config命令帮助."""
        result = runner.invoke(cli, ["config", "--help"])

        assert result.exit_code == 0
        assert "配置管理" in result.output

    def test_config_command_show(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试config命令显示配置."""
        # Run in isolated directory
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["config", "--show"])

            assert result.exit_code == 0
            # Output format changed - checks for current config section
            assert "当前配置:" in result.output or "未找到配置文件" in result.output

    def test_config_command_set(self, runner: CliRunner) -> None:
        """测试config命令设置配置."""
        result = runner.invoke(cli, ["config", "--set", "project.path=/new/path"])

        assert result.exit_code == 0
        assert "设置配置: project.path = /new/path" in result.output
