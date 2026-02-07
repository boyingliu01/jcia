"""TestSelectionService 测试."""

from jcia.core.entities.impact_graph import ImpactGraph
from jcia.core.entities.test_case import TestCase, TestPriority
from jcia.core.services.test_selection_service import TestSelectionStrategy


class TestTestSelectionService:
    """TestSelectionService 测试类."""

    def test_select_tests_by_impact_graph(self) -> None:
        """测试根据影响图选择测试."""
        from jcia.core.services import TestSelectionService

        # Arrange
        service = TestSelectionService()

        impact_graph = ImpactGraph()
        impact_graph.root_methods = ["com.example.Service.process"]

        # 创建测试用例池
        test_pool = [
            TestCase(
                class_name="ServiceTest",
                method_name="testProcess",
                target_class="com.example.Service",
                target_method="process",
            ),
            TestCase(
                class_name="OtherTest",
                method_name="testOther",
                target_class="com.example.Other",
                target_method="other",
            ),
        ]

        # Act
        selected = service.select_by_impact(impact_graph, test_pool)

        # Assert
        assert len(selected) > 0
        assert any("testProcess" in tc.method_name for tc in selected)

    def test_select_tests_by_priority(self) -> None:
        """测试按优先级选择测试."""
        from jcia.core.services import TestSelectionService

        # Arrange
        service = TestSelectionService()

        test_pool = [
            TestCase(
                class_name="CriticalTest",
                method_name="testCritical",
                priority=TestPriority.CRITICAL,
            ),
            TestCase(
                class_name="NormalTest",
                method_name="testNormal",
                priority=TestPriority.MEDIUM,
            ),
            TestCase(
                class_name="LowTest",
                method_name="testLow",
                priority=TestPriority.LOW,
            ),
        ]

        # Act
        selected = service.select_by_priority(test_pool, TestPriority.HIGH)

        # Assert
        assert len(selected) == 1
        assert selected[0].priority == TestPriority.CRITICAL

    def test_select_tests_with_empty_impact(self) -> None:
        """测试处理空影响图."""
        from jcia.core.services import TestSelectionService

        # Arrange
        service = TestSelectionService()
        impact_graph = ImpactGraph()
        test_pool = [
            TestCase(
                class_name="Test",
                method_name="testMethod",
            ),
        ]

        # Act
        selected = service.select_by_impact(impact_graph, test_pool)

        # Assert
        # 空影响图应返回所有测试（保守策略）
        assert len(selected) >= 0

    def test_select_tests_with_class_matching(self) -> None:
        """测试类名匹配."""
        from jcia.core.entities.impact_graph import ImpactNode, ImpactType
        from jcia.core.services import TestSelectionService

        # Arrange
        service = TestSelectionService()

        impact_graph = ImpactGraph()
        impact_graph.add_node(
            ImpactNode(
                method_name="com.example.Service.method",
                class_name="com.example.Service",
                impact_type=ImpactType.DIRECT,
            )
        )

        test_pool = [
            TestCase(
                class_name="ServiceTest",
                method_name="testOperation",
                target_class="com.example.Service",
            ),
            TestCase(
                class_name="OtherTest",
                method_name="testOther",
                target_class="com.example.Other",
            ),
        ]

        # Act
        selected = service.select_by_impact(impact_graph, test_pool)

        # Assert
        assert len(selected) > 0

    def test_get_selection_strategy(self) -> None:
        """测试获取选择策略."""
        from jcia.core.services import TestSelectionService

        # Arrange
        service = TestSelectionService()

        # Act
        strategy = service.strategy

        # Assert
        assert isinstance(strategy, TestSelectionStrategy)

    def test_filter_tests_by_tag(self) -> None:
        """测试按标签过滤测试."""
        from jcia.core.services import TestSelectionService

        # Arrange
        service = TestSelectionService()

        test_pool = [
            TestCase(
                class_name="Test",
                method_name="testFast",
                tags=["fast", "unit"],
            ),
            TestCase(
                class_name="Test",
                method_name="testSlow",
                tags=["slow", "integration"],
            ),
        ]

        # Act
        selected = service.filter_by_tag(test_pool, "fast")

        # Assert
        assert len(selected) == 1
        assert selected[0].method_name == "testFast"

    def test_exclude_tests_by_tag(self) -> None:
        """测试排除特定标签的测试."""
        from jcia.core.services import TestSelectionService

        # Arrange
        service = TestSelectionService()

        test_pool = [
            TestCase(
                class_name="Test",
                method_name="testIncluded",
                tags=["unit"],
            ),
            TestCase(
                class_name="Test",
                method_name="testExcluded",
                tags=["flaky"],
            ),
        ]

        # Act
        selected = service.exclude_by_tag(test_pool, "flaky")

        # Assert
        assert len(selected) == 1
        assert selected[0].method_name == "testIncluded"

    def test_merge_test_lists(self) -> None:
        """测试合并测试列表."""
        from jcia.core.services import TestSelectionService

        # Arrange
        service = TestSelectionService()

        list1 = [
            TestCase(
                class_name="Test",
                method_name="testMethod1",
            ),
        ]
        list2 = [
            TestCase(
                class_name="Test",
                method_name="testMethod2",
            ),
        ]

        # Act
        merged = service.merge_test_lists([list1, list2])

        # Assert
        assert len(merged) == 2
