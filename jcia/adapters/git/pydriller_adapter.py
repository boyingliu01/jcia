"""PyDriller Git 适配器实现."""

from datetime import datetime
from pathlib import Path
from typing import Any

from pydriller import Git  # type: ignore[import-untyped]

from jcia.core.entities.change_set import (
    ChangeSet,
    ChangeType,
    CommitInfo,
    FileChange,
    MethodChange,
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

        git = Git(self._repo_path)
        try:
            for commit in self._collect_commits(git, from_commit, to_commit):
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
        finally:
            git.clear()

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
        git: Any = None

        try:
            git = Git(self._repo_path)
            for commit in self._collect_commits(git, commit_hash, commit_hash):
                changed_methods = getattr(commit, "changed_methods", None)
                if not changed_methods:
                    continue

                for method in changed_methods:  # type: ignore[assignment]
                    long_name = getattr(method, "long_name", None)
                    if long_name:
                        methods.append(long_name)
        except Exception:
            # 返回空列表而不是抛出异常，处理不存在的提交等情况
            return []
        finally:
            if git is not None:
                git.clear()

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

    def _collect_commits(self, git: Any, from_commit: str, to_commit: str | None) -> list[Any]:
        """可靠枚举闭区间 [from_commit, to_commit] 内的 PyDriller Commit 对象.

        绕过 ``Repository.traverse_commits()`` 的 ``--ancestry-path`` rev 构造：
        该构造在 Windows 新建仓库上会间歇性地把 from_commit 解析出错误的父提交
        数量，进而生成含 ``<from>^`` 的非法 rev，使 ``git rev-list`` 返回空结果
        （实测约 30% 概率，且对同一仓库粘滞复现、重试无效）。改用 GitPython 的
        简单 range ``<from>..<to>``（实测 100% 可靠）枚举，再前置 from_commit
        本身以复现 PyDriller 的闭区间语义；随后用 PyDriller 的
        ``get_commit_from_gitpython`` 包装，完整保留 modified_files /
        changed_methods 等 Java 解析能力。

        Args:
            git: 已打开的 PyDriller Git 对象（由调用方负责 clear）
            from_commit: 起始提交（闭区间，包含自身）
            to_commit: 结束提交（默认 HEAD）

        Returns:
            list[Any]: 按时间升序排列的 PyDriller Commit 对象列表
        """
        repo = git.repo
        start = repo.commit(from_commit)
        to_ref = to_commit or "HEAD"
        raw_commits: list[Any] = [start]
        raw_commits.extend(repo.iter_commits(rev=f"{start.hexsha}..{to_ref}", reverse=True))
        return [git.get_commit_from_gitpython(rc) for rc in raw_commits]

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

        # PyDriller 的 filename 仅为 basename（如 "Service.java"），无法用于
        # 定位磁盘文件；new_path 才是相对仓库根目录的完整路径。统一分隔符为
        # 正斜杠，保证跨平台一致、下游 ``repo_path / file_path`` 拼接正确，
        # 并使 is_test_file 的 "/test/" 判断生效。缺失时回退 filename。
        raw_path = getattr(pydriller_file, "new_path", None) or getattr(
            pydriller_file, "filename", ""
        )
        file_path = raw_path.replace("\\", "/") if raw_path else ""

        raw_old_path = getattr(pydriller_file, "old_path", None)
        old_path = raw_old_path.replace("\\", "/") if raw_old_path else None

        file_change = FileChange(
            file_path=file_path,
            change_type=change_type,
            old_path=old_path,
            insertions=getattr(pydriller_file, "added_lines", 0) or 0,
            deletions=getattr(pydriller_file, "deleted_lines", 0) or 0,
        )

        # 提取方法级变更（仅针对 Java 文件）
        if file_change.is_java_file:
            changed_methods = getattr(pydriller_file, "changed_methods", []) or []
            for method in changed_methods:
                method_entity = self._convert_method_change(method)
                file_change.method_changes.append(method_entity)

        return file_change

    def _convert_method_change(self, pydriller_method: Any) -> MethodChange:
        """转换 PyDriller 方法变更为领域实体.

        Args:
            pydriller_method: PyDriller 方法对象

        Returns:
            MethodChange: 方法变更实体
        """
        long_name = getattr(pydriller_method, "long_name", "")
        # 改进的类名和签名提取逻辑
        class_name = ""
        method_name = getattr(pydriller_method, "name", "")
        signature = None

        if "(" in long_name:
            # 分离方法名部分和签名部分
            parts = long_name.split("(", 1)
            name_part = parts[0]
            signature = "(" + parts[1]

            # 提取类名（去掉方法名后的剩余部分）
            if "." in name_part:
                # 处理 com.example.Class.method 的情况
                class_parts = name_part.split(".")
                # 最后一个部分是方法名
                if method_name and class_parts[-1] == method_name:
                    class_name = ".".join(class_parts[:-1])
                elif len(class_parts) >= 2:
                    # 如果无法匹配，假设倒数第二个是类名
                    class_name = ".".join(class_parts[:-1])
        elif "." in long_name:
            # 没有签名，只有类名和方法名
            class_parts = long_name.split(".")
            if (method_name and class_parts[-1] == method_name) or len(class_parts) >= 2:
                class_name = ".".join(class_parts[:-1])

        # 验证并清理签名
        if signature and not signature.endswith(")"):
            signature = signature.rstrip(",") + ")"

        return MethodChange(
            class_name=class_name,
            method_name=method_name,
            signature=signature,
            change_type=ChangeType.MODIFY,  # pydriller.changed_methods 通常表示修改
            line_start=getattr(pydriller_method, "start_line", 0),
            line_end=getattr(pydriller_method, "end_line", 0),
        )
