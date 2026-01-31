"""MavenAdapter 单元测试."""

from unittest.mock import Mock, patch

from jcia.adapters.maven.maven_adapter import MavenAdapter
from jcia.core.interfaces.tool_wrapper import ToolStatus


class TestMavenAdapter:
    """MavenAdapter 测试类."""

    def test_tool_name_returns_maven(self) -> None:
        """测试工具名称."""
        # Arrange
        adapter = MavenAdapter(project_path="/fake/project")

        # Act
        name = adapter.tool_name

        # Assert
        assert name == "maven"

    def test_tool_type_is_coverage(self) -> None:
        """测试工具类型."""
        # Arrange
        adapter = MavenAdapter(project_path="/fake/project")

        # Act
        tool_type = adapter.tool_type

        # Assert
        from jcia.core.interfaces.tool_wrapper import ToolType

        assert tool_type == ToolType.COVERAGE

    def test_init_stores_project_path(self) -> None:
        """测试初始化存储项目路径."""
        # Arrange & Act
        adapter = MavenAdapter(project_path="/test/project")

        # Assert
        assert adapter._project_path == "/test/project"

    @patch("jcia.adapters.maven.maven_adapter.Path.exists")
    def test_check_status_when_maven_installed(self, mock_exists) -> None:
        """测试检查Maven状态（已安装）。"""
        # Arrange
        adapter = MavenAdapter(project_path="/test/project")
        mock_exists.return_value = True

        # Act
        status = adapter.check_status()

        # Assert
        assert status == ToolStatus.READY

    @patch("jcia.adapters.maven.maven_adapter.Path.exists")
    def test_check_status_when_maven_not_installed(self, mock_exists) -> None:
        """测试检查Maven状态（未安装）。"""
        # Arrange
        adapter = MavenAdapter(project_path="/test/project")
        mock_exists.return_value = False

        # Act
        status = adapter.check_status()

        # Assert
        assert status == ToolStatus.NOT_INSTALLED

    @patch("subprocess.run")
    def test_get_version_returns_version(self, mock_run) -> None:
        """测试获取Maven版本."""
        # Arrange
        adapter = MavenAdapter(project_path="/test/project")
        mock_run.return_value = Mock(stdout="Apache Maven 3.9.5 (1234567)", returncode=0)

        # Act
        version = adapter.get_version()

        # Assert
        assert version == "3.9.5 (1234567)"

    @patch("subprocess.run")
    def test_execute_maven_command_success(self, mock_run) -> None:
        """测试执行Maven命令成功。"""
        # Arrange
        adapter = MavenAdapter(project_path="/test/project")
        mock_run.return_value = Mock(stdout="Build success", stderr="", returncode=0)

        # Act
        result = adapter.execute(["mvn", "compile"])

        # Assert
        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "Build success"

    @patch("subprocess.run")
    def test_execute_maven_command_failure(self, mock_run) -> None:
        """测试执行Maven命令失败。"""
        # Arrange
        adapter = MavenAdapter(project_path="/test/project")
        mock_run.return_value = Mock(stdout="", stderr="Build failed", returncode=1)

        # Act
        result = adapter.execute(["mvn", "test"])

        # Assert
        assert result.success is False
        assert result.exit_code == 1
        assert result.stderr == "Build failed"
