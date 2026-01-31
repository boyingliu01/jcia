"""仓储模式抽象接口定义.

遵循仓储模式，将数据访问逻辑与业务逻辑分离。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jcia.core.entities.test_run import TestDiff, TestResult, TestRun


class TestRunRepository(ABC):
    """测试运行仓储接口.

    负责TestRun实体的持久化操作。
    """

    @abstractmethod
    def save(self, test_run: "TestRun") -> int:
        """保存测试运行记录.

        Args:
            test_run: 测试运行实体

        Returns:
            int: 记录ID
        """
        pass

    @abstractmethod
    def find_by_id(self, run_id: int) -> "TestRun | None":
        """根据ID查询测试运行.

        Args:
            run_id: 运行ID

        Returns:
            Optional[TestRun]: 测试运行实体
        """
        pass

    @abstractmethod
    def find_by_commit(
        self,
        commit_hash: str,
        run_type: str | None = None,
    ) -> list["TestRun"]:
        """根据提交哈希查询测试运行.

        Args:
            commit_hash: 提交哈希
            run_type: 运行类型过滤（BASELINE/REGRESSION）

        Returns:
            list[TestRun]: 测试运行列表
        """
        pass

    @abstractmethod
    def find_latest(self, run_type: str | None = None) -> "TestRun | None":
        """查询最新的测试运行.

        Args:
            run_type: 运行类型过滤

        Returns:
            Optional[TestRun]: 最新的测试运行
        """
        pass

    @abstractmethod
    def update(self, test_run: "TestRun") -> bool:
        """更新测试运行记录.

        Args:
            test_run: 测试运行实体

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    def delete(self, run_id: int) -> bool:
        """删除测试运行记录.

        Args:
            run_id: 运行ID

        Returns:
            bool: 是否成功
        """
        pass


class TestResultRepository(ABC):
    """测试结果仓储接口."""

    @abstractmethod
    def save(self, test_result: "TestResult") -> int:
        """保存测试结果."""
        pass

    @abstractmethod
    def save_batch(self, results: list["TestResult"]) -> int:
        """批量保存测试结果."""
        pass

    @abstractmethod
    def find_by_run_id(self, run_id: int) -> list["TestResult"]:
        """根据运行ID查询测试结果."""
        pass

    @abstractmethod
    def find_failed_by_run_id(self, run_id: int) -> list["TestResult"]:
        """查询指定运行的失败测试."""
        pass


class TestDiffRepository(ABC):
    """测试差异仓储接口."""

    @abstractmethod
    def save(self, test_diff: "TestDiff") -> int:
        """保存测试差异."""
        pass

    @abstractmethod
    def save_batch(self, diffs: list["TestDiff"]) -> int:
        """批量保存测试差异."""
        pass

    @abstractmethod
    def find_by_run_ids(self, baseline_run_id: int, regression_run_id: int) -> list["TestDiff"]:
        """根据基线和回归运行ID查询差异."""
        pass

    @abstractmethod
    def find_unexpected_failures(
        self, baseline_run_id: int, regression_run_id: int
    ) -> list["TestDiff"]:
        """查询非预期的失败（基线通过，回归失败）."""
        pass


class ChangeImpactRepository(ABC):
    """变更影响仓储接口."""

    @abstractmethod
    def save_impact(self, commit_hash: str, impact_data: dict[str, object]) -> int:
        """保存变更影响数据."""
        pass

    @abstractmethod
    def find_by_commit(self, commit_hash: str) -> dict[str, object] | None:
        """根据提交查询影响数据."""
        pass

    @abstractmethod
    def find_latest(self) -> dict[str, object] | None:
        """查询最新的影响数据."""
        pass
