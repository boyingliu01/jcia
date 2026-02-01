"""PyDriller Git 适配器实现."""

from datetime import datetime
from pathlib import Path
from typing import Any

from pydriller import Repository  # type: ignore[import-untyped]

from jcia.core.entities.change_set import (
    ChangeSet,
    ChangeType,
    CommitInfo,
    FileChange,
)
from jcia.core.interfaces.analyzer import ChangeAnalyzer


class PyDrillerAdapter(ChangeAnalyzer):
    """PyDriller Git 仓库适配器.

    使用 PyDriller 库分析 Git 仓库中的提交差异。
    """

    def __init__(self, repo_path: str) -> None:
        """初始化适配器.

        Args:
            repo_path: Git 仓库路径
        """
        self._repo_path = repo_path

    def analyze_commits(self, from_commit: str, to_commit: str | None = None) -> ChangeSet:
        """分析指定提交范围的变更.

        Args:
            from_commit: 起始提交哈希
            to_commit: 结束提交哈希（默认为HEAD）

        Returns:
            ChangeSet: 变更集合，包含所有变更的文件和方法
        """
        self._ensure_repo_exists()

        change_set = ChangeSet(
            from_commit=from_commit,
            to_commit=to_commit,
        )

        commits = list(
            Repository(
                path_to_repo=self._repo_path,
                from_commit=from_commit,
                to_commit=to_commit or "HEAD",
            ).traverse_commits()
        )

        for commit in commits:
            author = getattr(commit, "author", None)
            parents = getattr(commit, "parents", []) or []
            commit_info = CommitInfo(
                hash=getattr(commit, "hash", ""),
                message=getattr(commit, "msg", "") or "",
                author=getattr(author, "name", "") or "",
                email=getattr(author, "email", "") or "",
                timestamp=getattr(commit, "author_date", datetime.min) or datetime.min,
                parents=[getattr(p, "hash", "") for p in parents],
            )
            change_set.commits.append(commit_info)

            for file_change in getattr(commit, "modified_files", []) or []:
                file_entity = self._convert_file_change(file_change)
                change_set.add_file_change(file_entity)

        return change_set

    def analyze_commit_range(self, commit_range: str) -> ChangeSet:
        """分析commit范围（如"abc123..def456"）.

        Args:
            commit_range: 提交范围字符串，支持git范围语法

        Returns:
            ChangeSet: 变更集合
        """
        # 解析提交范围
        if ".." in commit_range:
            from_commit, to_commit = commit_range.split("..", 1)
            return self.analyze_commits(from_commit.strip(), to_commit.strip())
        else:
            return self.analyze_commits(commit_range.strip())

    def get_changed_methods(self, commit_hash: str) -> list[str]:
        """获取指定提交中变更的方法列表.

        Args:
            commit_hash: 提交哈希

        Returns:
            List[str]: 变更的方法全限定名列表
        """
        self._ensure_repo_exists()

        methods: list[str] = []

        for commit in Repository(
            path_to_repo=self._repo_path,
            from_commit=commit_hash,
            to_commit=commit_hash,
        ).traverse_commits():
            changed_methods = getattr(commit, "changed_methods", None)
            if not changed_methods:
                continue

            for method in changed_methods:  # type: ignore[assignment]
                long_name = getattr(method, "long_name", None)
                if long_name:
                    methods.append(long_name)

        return methods

    @property
    def analyzer_name(self) -> str:
        """返回分析器名称.

        Returns:
            str: 分析器标识名称
        """
        return "pydriller"

    def _ensure_repo_exists(self) -> None:
        """校验仓库路径是否存在."""
        if not Path(self._repo_path).exists():
            raise FileNotFoundError(f"Repository path not found: {self._repo_path}")

    def _map_change_type(self, change_type_value: Any) -> ChangeType:
        """兼容字符串或枚举的变更类型映射."""
        change_type_map = {
            "ADD": ChangeType.ADD,
            "DELETE": ChangeType.DELETE,
            "MODIFY": ChangeType.MODIFY,
            "RENAME": ChangeType.RENAME,
        }

        if change_type_value is None:
            return ChangeType.MODIFY

        key = None
        if hasattr(change_type_value, "name"):
            key = str(change_type_value.name).upper()
        else:
            key = str(change_type_value).upper()

        return change_type_map.get(key, ChangeType.MODIFY)

    def _convert_file_change(self, pydriller_file: Any) -> FileChange:
        """转换 PyDriller 文件变更为领域实体.

        Args:
            pydriller_file: PyDriller 文件变更对象

        Returns:
            FileChange: 文件变更实体
        """
        change_type = self._map_change_type(getattr(pydriller_file, "change_type", None))

        return FileChange(
            file_path=getattr(pydriller_file, "filename", ""),
            change_type=change_type,
            insertions=getattr(pydriller_file, "added_lines", 0) or 0,
            deletions=getattr(pydriller_file, "deleted_lines", 0) or 0,
        )
