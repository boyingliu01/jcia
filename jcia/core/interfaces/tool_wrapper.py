"""工具封装抽象接口定义.

所有外部工具（PyDriller, java-all-call-graph等）都通过实现这些接口接入系统。
遵循开闭原则(OCP)，新增工具无需修改现有代码。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ToolType(Enum):
    """工具类型枚举."""

    CHANGE_DETECTION = "change_detection"
    CALL_GRAPH = "call_graph"
    TEST_SELECTION = "test_selection"
    TEST_GENERATION = "test_generation"
    COVERAGE = "coverage"
    MUTATION = "mutation"


class ToolStatus(Enum):
    """工具状态枚举."""

    READY = "ready"
    NOT_INSTALLED = "not_installed"
    VERSION_MISMATCH = "version_mismatch"
    ERROR = "error"


@dataclass
class ToolResult:
    """工具执行结果.

    Attributes:
        success: 是否成功
        exit_code: 进程退出码
        stdout: 标准输出
        stderr: 标准错误
        data: 解析后的数据（可选）
        error_message: 错误信息（失败时）
    """

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    data: dict[str, Any] | None = None
    error_message: str | None = None


class ToolWrapper(ABC):
    """工具封装抽象基类.

    所有外部工具适配器都必须继承此类。
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """初始化工具封装器.

        Args:
            config: 工具配置字典
        """
        self.config = config or {}

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """返回工具名称.

        Returns:
            str: 工具标识名称
        """
        pass

    @property
    @abstractmethod
    def tool_type(self) -> ToolType:
        """返回工具类型.

        Returns:
            ToolType: 工具类型枚举
        """
        pass

    @abstractmethod
    def check_status(self) -> ToolStatus:
        """检查工具状态.

        Returns:
            ToolStatus: 工具当前状态
        """
        pass

    @abstractmethod
    def install(self) -> bool:
        """安装/初始化工具.

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    def get_version(self) -> str | None:
        """获取工具版本.

        Returns:
            Optional[str]: 版本字符串，未安装返回None
        """
        pass

    @abstractmethod
    def execute(
        self, args: list[str], cwd: Path | None = None, timeout: int | None = None
    ) -> ToolResult:
        """执行工具命令.

        Args:
            args: 命令参数列表
            cwd: 工作目录
            timeout: 超时时间（秒）

        Returns:
            ToolResult: 执行结果
        """
        pass


class JavaToolWrapper(ToolWrapper, ABC):
    """Java工具封装抽象基类.

    专用于需要JVM的Java工具。
    """

    @property
    @abstractmethod
    def jar_path(self) -> Path:
        """返回JAR文件路径.

        Returns:
            Path: JAR文件路径
        """
        pass

    @abstractmethod
    def build_classpath(self) -> str:
        """构建类路径.

        Returns:
            str: 类路径字符串
        """
        pass


class MavenPluginWrapper(ToolWrapper, ABC):
    """Maven插件封装抽象基类.

    专用于Maven插件（STARTS, JaCoCo, Pitest等）。
    """

    @property
    @abstractmethod
    def plugin_group_id(self) -> str:
        """返回插件groupId."""
        pass

    @property
    @abstractmethod
    def plugin_artifact_id(self) -> str:
        """返回插件artifactId."""
        pass

    @abstractmethod
    def get_maven_goal(self) -> str:
        """返回Maven目标（如"starts:select"）."""
        pass

    @abstractmethod
    def build_maven_args(self, **kwargs: Any) -> list[str]:
        """构建Maven参数列表."""
        pass
