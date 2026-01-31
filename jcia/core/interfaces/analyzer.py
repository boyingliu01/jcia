"""分析器抽象接口定义.

遵循依赖倒置原则(DIP)，高层模块依赖此抽象而非具体实现。
"""

from abc import ABC, abstractmethod

from jcia.core.entities.change_set import ChangeSet
from jcia.core.entities.impact_graph import ImpactGraph


class ChangeAnalyzer(ABC):
    """变更分析器抽象接口.

    负责检测Git仓库中的代码变更，识别变更的文件和方法。

    Example:
        ```python
        analyzer: ChangeAnalyzer = PyDrillerAdapter(repo_path)
        changes = analyzer.analyze_commits("abc123", "def456")
        ```
    """

    @abstractmethod
    def analyze_commits(self, from_commit: str, to_commit: str | None = None) -> ChangeSet:
        """分析指定提交范围的变更.

        Args:
            from_commit: 起始提交哈希
            to_commit: 结束提交哈希（默认为HEAD）

        Returns:
            ChangeSet: 变更集合，包含所有变更的文件和方法

        Raises:
            AnalysisError: 分析过程中发生错误
            GitError: Git操作失败
        """
        pass

    @abstractmethod
    def analyze_commit_range(self, commit_range: str) -> ChangeSet:
        """分析commit范围（如"abc123..def456"）.

        Args:
            commit_range: 提交范围字符串，支持git范围语法

        Returns:
            ChangeSet: 变更集合
        """
        pass

    @abstractmethod
    def get_changed_methods(self, commit_hash: str) -> list[str]:
        """获取指定提交中变更的方法列表.

        Args:
            commit_hash: 提交哈希

        Returns:
            List[str]: 变更的方法全限定名列表
        """
        pass

    @property
    @abstractmethod
    def analyzer_name(self) -> str:
        """返回分析器名称.

        Returns:
            str: 分析器标识名称（如"pydriller", "gitpython"）
        """
        pass


class ImpactAnalyzer(ABC):
    """影响分析器抽象接口.

    负责基于调用链分析计算变更的影响范围。
    """

    @abstractmethod
    def calculate_impact(self, change_set: ChangeSet) -> ImpactGraph:
        """计算变更的影响范围.

        Args:
            change_set: 变更集合

        Returns:
            ImpactGraph: 影响图，包含所有受影响的方法
        """
        pass

    @abstractmethod
    def get_upstream_impact(self, method: str, max_depth: int = 10) -> list[str]:
        """获取指定方法的上游影响（调用该方法的方法）.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            List[str]: 上游方法列表
        """
        pass

    @abstractmethod
    def get_downstream_impact(self, method: str, max_depth: int = 10) -> list[str]:
        """获取指定方法的下游影响（被该方法调用的方法）.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            List[str]: 下游方法列表
        """
        pass
