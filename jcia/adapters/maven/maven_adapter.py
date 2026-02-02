"""Maven 适配器实现."""

import shutil
import subprocess  # nosec B404
from pathlib import Path

from jcia.core.interfaces.tool_wrapper import ToolResult, ToolStatus, ToolType


class MavenAdapter:
    """Maven 项目适配器。

    用于调用 Maven 命令和插件。
    """

    def __init__(self, project_path: str) -> None:
        """初始化适配器.

        Args:
            project_path: Maven 项目路径
        """
        self._project_path = project_path

    @property
    def tool_name(self) -> str:
        """返回工具名称."""
        return "maven"

    @property
    def tool_type(self) -> ToolType:
        """返回工具类型."""
        return ToolType.COVERAGE

    def check_status(self) -> ToolStatus:
        """检查工具状态."""
        pom_path = Path(self._project_path) / "pom.xml"
        if not pom_path.exists():
            return ToolStatus.NOT_INSTALLED

        if shutil.which("mvn") is None:
            return ToolStatus.NOT_INSTALLED

        return ToolStatus.READY

    def install(self) -> bool:
        """安装/初始化工具。

        Maven 通常已安装，此方法返回 True。
        """
        return True

    def get_version(self) -> str | None:
        """获取 Maven 版本."""
        try:
            result = subprocess.run(  # nosec B603 B607
                ["mvn", "-v"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return None

            if "Apache Maven" not in result.stdout:
                return None

            return result.stdout.split("Apache Maven", maxsplit=1)[1].strip()
        except FileNotFoundError:
            return None

    def execute(
        self, args: list[str] | None = None, cwd: Path | None = None, timeout: int | None = None
    ) -> ToolResult:
        """执行 Maven 命令。

        Args:
            args: 命令参数列表
            cwd: 工作目录
            timeout: 超时时间（秒）

        Returns:
            ToolResult: 执行结果
        """
        if cwd is None:
            cwd = Path(self._project_path)

        mvn_path = shutil.which("mvn")
        if mvn_path is None:
            return ToolResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="mvn executable not found",
            )

        normalized_args = self._normalize_args(args or [])
        cmd = [mvn_path] + normalized_args

        try:
            result = subprocess.run(  # nosec B603
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ToolResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
            )

    def plugin_group_id(self) -> str:
        """返回插件 groupId。"""
        return "org.apache.maven.plugins"

    def plugin_artifact_id(self) -> str:
        """返回插件 artifactId。"""
        return "maven-surefire-plugin"

    def get_maven_goal(self) -> str:
        """返回 Maven 目标（如"surefire:test"）。"""
        return "surefire:test"

    def build_maven_args(self, **kwargs: bool) -> list[str]:
        """构建 Maven 参数列表。"""
        args = ["clean", "test"]
        if "skip_tests" in kwargs and kwargs["skip_tests"]:
            # 正确的 Maven 跳过测试参数是 -DskipTests
            args.append("-DskipTests")
        return args

    def _normalize_args(self, args: list[str]) -> list[str]:
        """移除前导 mvn 前缀，保证命令唯一。"""
        if not args:
            return []

        normalized = list(args)
        while normalized and normalized[0].lower().startswith("mvn"):
            normalized.pop(0)
        return normalized
