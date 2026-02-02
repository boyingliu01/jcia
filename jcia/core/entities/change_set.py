"""变更集合领域实体.

表示Git仓库中的一组变更，包括变更的文件和方法。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ChangeType(Enum):
    """变更类型枚举."""

    ADD = "add"  # 新增
    MODIFY = "modify"  # 修改
    DELETE = "delete"  # 删除
    RENAME = "rename"  # 重命名


class ChangeStatus(Enum):
    """变更状态枚举."""

    UNSTAGED = "unstaged"
    STAGED = "staged"
    COMMITTED = "committed"


@dataclass
class MethodChange:
    """方法级变更.

    Attributes:
        class_name: 类名
        method_name: 方法名
        signature: 方法签名
        change_type: 变更类型
        old_content: 旧代码内容
        new_content: 新代码内容
        line_start: 起始行号
        line_end: 结束行号
    """

    class_name: str
    method_name: str
    signature: str | None = None
    change_type: ChangeType = ChangeType.MODIFY
    old_content: str | None = None
    new_content: str | None = None
    line_start: int = 0
    line_end: int = 0

    @property
    def full_name(self) -> str:
        """返回方法全限定名."""
        if self.signature:
            return f"{self.class_name}.{self.method_name}{self.signature}"
        return f"{self.class_name}.{self.method_name}"

    @property
    def is_new(self) -> bool:
        """是否是新增方法."""
        return self.change_type == ChangeType.ADD

    @property
    def is_deleted(self) -> bool:
        """是否是删除方法."""
        return self.change_type == ChangeType.DELETE


@dataclass
class FileChange:
    """文件级变更.

    Attributes:
        file_path: 文件路径
        change_type: 变更类型
        old_path: 旧路径（重命名时）
        insertions: 新增行数
        deletions: 删除行数
        method_changes: 方法级变更列表
    """

    file_path: str
    change_type: ChangeType = ChangeType.MODIFY
    old_path: str | None = None
    insertions: int = 0
    deletions: int = 0
    method_changes: list[MethodChange] = field(default_factory=list)

    @property
    def is_java_file(self) -> bool:
        """是否是Java文件."""
        return self.file_path.endswith(".java")

    @property
    def is_test_file(self) -> bool:
        """是否是测试文件."""
        # 统一路径分隔符为正斜杠进行判断，增加 Windows 兼容性
        normalized_path = self.file_path.replace("\\", "/").lower()
        return (
            normalized_path.endswith("test.java")
            or normalized_path.endswith("tests.java")
            or "/test/" in normalized_path
        )

    @property
    def total_changes(self) -> int:
        """总变更行数."""
        return self.insertions + self.deletions


@dataclass
class CommitInfo:
    """提交信息.

    Attributes:
        hash: 提交哈希
        message: 提交消息
        author: 作者
        email: 作者邮箱
        timestamp: 提交时间
        parents: 父提交哈希列表
    """

    hash: str
    message: str
    author: str
    email: str
    timestamp: datetime
    parents: list[str] = field(default_factory=list)

    @property
    def short_hash(self) -> str:
        """返回短哈希（前7位）."""
        return self.hash[:7] if len(self.hash) >= 7 else self.hash

    @property
    def title(self) -> str:
        """返回提交标题（第一行）."""
        return self.message.split("\n")[0] if self.message else ""


@dataclass
class ChangeSet:
    """变更集合.

    表示一个或多个提交的所有变更。

    Attributes:
        from_commit: 起始提交
        to_commit: 结束提交
        commits: 包含的提交列表
        file_changes: 文件变更列表
        status: 变更状态
    """

    from_commit: str | None = None
    to_commit: str | None = None
    commits: list[CommitInfo] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)
    status: ChangeStatus = ChangeStatus.COMMITTED

    @property
    def changed_files(self) -> list[str]:
        """返回所有变更文件路径."""
        return [fc.file_path for fc in self.file_changes]

    @property
    def changed_java_files(self) -> list[str]:
        """返回变更的Java文件路径."""
        return [fc.file_path for fc in self.file_changes if fc.is_java_file]

    @property
    def changed_methods(self) -> list[str]:
        """返回所有变更的方法全限定名."""
        methods = []
        for fc in self.file_changes:
            for mc in fc.method_changes:
                methods.append(mc.full_name)
        return methods

    @property
    def total_insertions(self) -> int:
        """总新增行数."""
        return sum(fc.insertions for fc in self.file_changes)

    @property
    def total_deletions(self) -> int:
        """总删除行数."""
        return sum(fc.deletions for fc in self.file_changes)

    @property
    def commit_count(self) -> int:
        """提交数量."""
        return len(self.commits)

    def get_file_change(self, file_path: str) -> FileChange | None:
        """获取指定文件的变更.

        Args:
            file_path: 文件路径

        Returns:
            Optional[FileChange]: 文件变更对象
        """
        for fc in self.file_changes:
            if fc.file_path == file_path:
                return fc
        return None

    def add_file_change(self, file_change: FileChange) -> None:
        """添加文件变更.

        Args:
            file_change: 文件变更对象
        """
        self.file_changes.append(file_change)

    def is_empty(self) -> bool:
        """是否为空变更集."""
        return len(self.file_changes) == 0

    def to_dict(self) -> dict[str, object]:
        """转换为字典."""
        return {
            "from_commit": self.from_commit,
            "to_commit": self.to_commit,
            "commit_count": self.commit_count,
            "changed_files": self.changed_files,
            "changed_methods": self.changed_methods,
            "total_insertions": self.total_insertions,
            "total_deletions": self.total_deletions,
        }
