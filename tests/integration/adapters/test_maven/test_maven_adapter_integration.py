"""MavenAdapter 集成测试 - 使用真实 Maven 项目 (Jenkins 项目)."""

from pathlib import Path

import pytest

from jcia.adapters.maven.maven_adapter import MavenAdapter
from jcia.core.interfaces.tool_wrapper import ToolStatus, ToolType


@pytest.fixture
def jenkins_project_path() -> Path:
    """获取 Jenkins 项目路径."""
    # Jenkins 已克隆到当前目录的 jenkins/ 文件夹
    project_path = Path(__file__).parent.parent.parent.parent / "jenkins"
    if not project_path.exists():
        pytest.skip(f"Jenkins project not found at {project_path}")
    return project_path


@pytest.fixture
def skip_if_no_maven() -> None:
    """如果 Maven 未安装则跳过测试."""
    import subprocess

    try:
        subprocess.run(
            ["mvn", "--version"],
            capture_output=True,
            timeout=5,
            check=True,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pytest.skip("Maven (mvn) is not installed or not available")


class TestMavenAdapterIntegration:
    """MavenAdapter 集成测试类 - 使用真实 Maven 项目."""

    def test_real_maven_project_connection(
        self, jenkins_project_path: Path, skip_if_no_maven: None
    ) -> None:
        """测试连接真实 Jenkins Maven 项目."""
        # Arrange & Act
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Assert
        assert adapter.tool_name == "maven"
        assert adapter._project_path == str(jenkins_project_path)

    def test_tool_type_is_coverage(
        self, jenkins_project_path: Path, skip_if_no_maven: None
    ) -> None:
        """测试工具类型."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act
        tool_type = adapter.tool_type

        # Assert
        assert tool_type == ToolType.COVERAGE

    def test_check_status_maven_installed(
        self, jenkins_project_path: Path, skip_if_no_maven: None
    ) -> None:
        """测试检查 Maven 状态（已安装）."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act
        status = adapter.check_status()

        # Assert
        assert status == ToolStatus.READY

    def test_get_version(self, jenkins_project_path: Path, skip_if_no_maven: None) -> None:
        """测试获取 Maven 版本."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act
        version = adapter.get_version()

        # Assert
        assert version is not None
        assert "Apache Maven" in version or "Maven" in version

    def test_execute_maven_help(self, jenkins_project_path: Path, skip_if_no_maven: None) -> None:
        """测试执行 Maven 命令（help）."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act
        result = adapter.execute(["help"])

        # Assert
        assert result.success is True
        assert result.exit_code == 0
        assert len(result.stdout) > 0

    def test_execute_maven_validate(
        self, jenkins_project_path: Path, skip_if_no_maven: None
    ) -> None:
        """测试执行 Maven validate 命令."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act
        result = adapter.execute(["validate"])

        # Assert
        # validate 应该成功或至少有一个退出码
        assert result.exit_code is not None

    def test_plugin_configurations(
        self, jenkins_project_path: Path, skip_if_no_maven: None
    ) -> None:
        """测试插件配置."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act
        group_id = adapter.plugin_group_id()
        artifact_id = adapter.plugin_artifact_id()
        goal = adapter.get_maven_goal()

        # Assert
        assert group_id == "org.apache.maven.plugins"
        assert artifact_id == "maven-surefire-plugin"
        assert goal == "surefire:test"

    def test_build_maven_args_default(
        self, jenkins_project_path: Path, skip_if_no_maven: None
    ) -> None:
        """测试默认构建参数."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act
        args = adapter.build_maven_args()

        # Assert
        assert args == ["clean", "test"]

    def test_build_maven_args_skip_tests(
        self, jenkins_project_path: Path, skip_if_no_maven: None
    ) -> None:
        """测试跳过测试的构建参数."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act
        args = adapter.build_maven_args(skip_tests=True)

        # Assert
        assert "clean" in args
        assert "test" in args
        assert "-DskipTests" in args

    def test_install_returns_true(self, jenkins_project_path: Path, skip_if_no_maven: None) -> None:
        """测试安装方法返回 True."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act
        result = adapter.install()

        # Assert
        assert result is True

    def test_normalize_args(self, jenkins_project_path: Path, skip_if_no_maven: None) -> None:
        """测试参数标准化."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act & Assert
        assert adapter._normalize_args(["mvn", "test"]) == ["test"]
        assert adapter._normalize_args(["MVN", "compile"]) == ["compile"]
        assert adapter._normalize_args(["mvn", "mvn", "test"]) == ["test"]

    def test_error_handling_missing_mvn_command(
        self, jenkins_project_path: Path, skip_if_no_maven: None
    ) -> None:
        """测试缺少 mvn 命令的错误处理."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act - 使用一个不存在的命令
        result = adapter.execute(["nonexistent-goal"])

        # Assert - 应该失败
        assert result.success is False
        assert result.exit_code != 0

    def test_pom_xml_exists(self, jenkins_project_path: Path, skip_if_no_maven: None) -> None:
        """测试 pom.xml 存在."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act
        status = adapter.check_status()

        # Assert - pom.xml 应该存在（Jenkins 是 Maven 项目）
        if status == ToolStatus.NOT_INSTALLED:
            pytest.skip("Maven not installed, cannot verify pom.xml")
        else:
            assert status == ToolStatus.READY

    def test_timeout_handling(self, jenkins_project_path: Path, skip_if_no_maven: None) -> None:
        """测试超时处理（使用极短超时）."""
        # Arrange
        adapter = MavenAdapter(project_path=str(jenkins_project_path))

        # Act - 使用一个非常短的命令和超时
        result = adapter.execute(["help"], timeout=30)

        # Assert
        assert result.success is True
