"""测试选择领域领域服务.

根据影响分析结果选择需要执行的测试用例。
"""

from jcia.core.entities.impact_graph import ImpactGraph
from jcia.core.entities.test_case import TestCase, TestPriority
from jcia.core.interfaces.test_runner import TestSelectionStrategy


class TestSelectionService:
    """测试选择服务.

    根据影响范围和测试策略选择需要执行的测试用例。
    """

    def __init__(
        self, strategy: TestSelectionStrategy = TestSelectionStrategy.IMPACT_BASED
    ) -> None:
        """初始化服务.

        Args:
            strategy: 默认选择策略
        """
        self._strategy = strategy

    def select_by_impact(
        self, impact_graph: ImpactGraph, test_pool: list[TestCase]
    ) -> list[TestCase]:
        """根据影响图选择测试.

        Args:
            impact_graph: 影响图
            test_pool: 测试用例池

        Returns:
            List[TestCase]: 选中的测试用例
        """
        if impact_graph.total_affected_methods == 0:
            # 空影响图，保守策略返回所有测试
            return test_pool.copy()

        selected: list[TestCase] = []
        affected_classes = impact_graph.affected_classes
        affected_methods = set(impact_graph.nodes.keys())

        for test_case in test_pool:
            if self._is_test_affected(test_case, affected_classes, affected_methods):
                selected.append(test_case)

        return selected

    def select_by_priority(
        self, test_pool: list[TestCase], min_priority: TestPriority
    ) -> list[TestCase]:
        """按优先级选择测试.

        Args:
            test_pool: 测试用例池
            min_priority: 最低优先级

        Returns:
            List[TestCase]: 选中的测试用例
        """
        priority_order = [
            TestPriority.CRITICAL,
            TestPriority.HIGH,
            TestPriority.MEDIUM,
            TestPriority.LOW,
        ]

        min_index = priority_order.index(min_priority)
        result: list[TestCase] = []

        for test_case in test_pool:
            try:
                test_index = priority_order.index(test_case.priority)
                if test_index <= min_index:
                    result.append(test_case)
            except ValueError:
                # 未知优先级，默认包含
                result.append(test_case)

        return result

    def filter_by_tag(self, test_pool: list[TestCase], tag: str) -> list[TestCase]:
        """按标签过滤测试.

        Args:
            test_pool: 测试用例池
            tag: 标签

        Returns:
            List[TestCase]: 包含指定标签的测试用例
        """
        return [tc for tc in test_pool if tag in tc.tags]

    def exclude_by_tag(self, test_pool: list[TestCase], tag: str) -> list[TestCase]:
        """排除包含特定标签的测试.

        Args:
            test_pool: 测试用例池
            tag: 标签

        Returns:
            List[TestCase]: 不包含指定标签的测试用例
        """
        return [tc for tc in test_pool if tag not in tc.tags]

    def merge_test_lists(self, test_lists: list[list[TestCase]]) -> list[TestCase]:
        """合并多个测试列表，去重.

        Args:
            test_lists: 测试列表的列表

        Returns:
            List[TestCase]: 合并后的测试列表
        """
        seen = set()
        result: list[TestCase] = []

        for test_list in test_lists:
            for test_case in test_list:
                test_key = test_case.full_name
                if test_key not in seen:
                    seen.add(test_key)
                    result.append(test_case)

        return result

    def get_strategy_for_impact(self, impact_graph: ImpactGraph) -> TestSelectionStrategy:
        """根据影响范围确定选择策略.

        Args:
            impact_graph: 影响图

        Returns:
            TestSelectionStrategy: 推荐的选择策略
        """
        if impact_graph.total_affected_methods == 0:
            return TestSelectionStrategy.ALL

        if impact_graph.high_severity_count > 0:
            # 高风险变更，运行所有测试
            return TestSelectionStrategy.ALL

        if impact_graph.total_affected_methods > 20:
            # 大量变更，使用影响范围选择
            return TestSelectionStrategy.IMPACT_BASED

        return TestSelectionStrategy.HYBRID

    @property
    def strategy(self) -> TestSelectionStrategy:
        """获取当前选择策略."""
        return self._strategy

    def set_strategy(self, strategy: TestSelectionStrategy) -> None:
        """设置选择策略.

        Args:
            strategy: 新的选择策略
        """
        self._strategy = strategy

    def _is_test_affected(
        self,
        test_case: TestCase,
        affected_classes: set[str],
        affected_methods: set[str],
    ) -> bool:
        """判断测试是否受影响.

        Args:
            test_case: 测试用例
            affected_classes: 受影响的类集合
            affected_methods: 受影响的方法集合

        Returns:
            bool: 是否受影响
        """
        # 检查目标类
        if test_case.target_class and test_case.target_class in affected_classes:
            return True

        # 检查目标方法
        if test_case.target_method:
            for method in affected_methods:
                if test_case.target_method in method:
                    return True

        # 检查测试类名是否包含受影响类名
        for affected_class in affected_classes:
            class_name = affected_class.split(".")[-1]
            if class_name in test_case.class_name:
                return True

        return False
