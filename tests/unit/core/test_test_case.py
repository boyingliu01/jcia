"""TestCase 与 TestSuite 实体单元测试."""

from __future__ import annotations

from pathlib import Path

from jcia.core.entities.test_case import (
    TestCase,
    TestPriority,
    TestSuite,
    TestType,
)


class TestTestCase:
    """TestCase 行为测试."""

    def test_full_name_and_to_maven_test(self) -> None:
        case = TestCase(class_name="com.example.ServiceTest", method_name="testDo")
        assert case.full_name == "com.example.ServiceTest#testDo"
        assert case.to_maven_test() == "com.example.ServiceTest#testDo"

    def test_flags_generated_unit_and_critical(self) -> None:
        generated = TestCase(
            class_name="G",
            method_name="m",
            test_type=TestType.GENERATED,
            priority=TestPriority.CRITICAL,
        )
        unit = TestCase(class_name="U", method_name="m", test_type=TestType.UNIT)

        assert generated.is_generated is True
        assert generated.is_unit_test is False
        assert generated.is_critical is True
        assert unit.is_unit_test is True

    def test_tags_priority_and_targets(self) -> None:
        case = TestCase(
            class_name="C",
            method_name="m",
            priority=TestPriority.HIGH,
            target_class="Target",
            target_method="do",
            tags=["slow", "db"],
        )
        assert "slow" in case.tags and "db" in case.tags
        assert case.priority == TestPriority.HIGH
        assert case.target_class == "Target"
        assert case.target_method == "do"

    def test_to_dict_serializes_path_and_metadata(self) -> None:
        case = TestCase(
            class_name="C",
            method_name="m",
            file_path=Path("tests/C.java"),
            line_number=42,
            tags=["smoke"],
            metadata={"owner": "qa"},
        )

        data = case.to_dict()
        assert data["full_name"] == "C#m"
        assert data["file_path"] == str(Path("tests/C.java"))
        assert data["line_number"] == 42
        assert data["tags"] == ["smoke"]


class TestTestSuite:
    """TestSuite 行为测试."""

    def test_add_and_count_tests(self) -> None:
        suite = TestSuite(name="suite")
        suite.add_test(TestCase(class_name="A", method_name="m1", priority=TestPriority.CRITICAL))
        suite.add_test(TestCase(class_name="B", method_name="m2", priority=TestPriority.MEDIUM))

        assert suite.test_count == 2
        assert len(suite.test_cases) == 2

    def test_filters_by_priority_and_tag(self) -> None:
        suite = TestSuite(name="suite")
        critical = TestCase(
            class_name="A",
            method_name="m1",
            priority=TestPriority.CRITICAL,
            tags=["smoke"],
        )
        generated = TestCase(
            class_name="B",
            method_name="m2",
            test_type=TestType.GENERATED,
            tags=["db", "smoke"],
        )

        suite.add_test(critical)
        suite.add_test(generated)

        assert suite.critical_tests == [critical]
        assert suite.generated_tests == [generated]
        assert suite.filter_by_priority(TestPriority.CRITICAL) == [critical]
        assert suite.filter_by_tag("smoke") == [critical, generated]

    def test_to_maven_test_list_and_dict(self) -> None:
        suite = TestSuite(name="suite", description="demo")
        case1 = TestCase(class_name="A", method_name="m1")
        case2 = TestCase(class_name="B", method_name="m2")
        suite.add_test(case1)
        suite.add_test(case2)

        maven_list = suite.to_maven_test_list()
        assert maven_list == ["A#m1", "B#m2"]

        data = suite.to_dict()
        assert data["name"] == "suite"
        assert data["test_count"] == 2
        assert data["description"] == "demo"
        assert len(data["test_cases"]) == 2
        assert data["test_cases"][0]["full_name"] == "A#m1"
