"""测试用例领域实体."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TestType(Enum):
    """测试类型枚举."""

    UNIT = "unit"  # 单元测试
    INTEGRATION = "integration"  # 集成测试
    GENERATED = "generated"  # 自动生成的测试
    MANUAL = "manual"  # 手工编写的测试


class TestPriority(Enum):
    """测试优先级枚举."""

    CRITICAL = "critical"  # 关键测试
    HIGH = "high"  # 高优先级
    MEDIUM = "medium"  # 中优先级
    LOW = "low"  # 低优先级


@dataclass
class TestCase:
    """测试用例.

    Attributes:
        class_name: 测试类名
        method_name: 测试方法名
        test_type: 测试类型
        priority: 优先级
        target_class: 被测试的目标类
        target_method: 被测试的目标方法
        file_path: 测试文件路径
        line_number: 测试方法行号
        tags: 测试标签
        metadata: 额外元数据
    """

    class_name: str
    method_name: str
    test_type: TestType = TestType.UNIT
    priority: TestPriority = TestPriority.MEDIUM
    target_class: str | None = None
    target_method: str | None = None
    file_path: Path | None = None
    line_number: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        """返回测试全限定名."""
        return f"{self.class_name}#{self.method_name}"

    @property
    def is_generated(self) -> bool:
        """是否是自动生成的测试."""
        return self.test_type == TestType.GENERATED

    @property
    def is_unit_test(self) -> bool:
        """是否是单元测试."""
        return self.test_type == TestType.UNIT

    @property
    def is_critical(self) -> bool:
        """是否是关键测试."""
        return self.priority == TestPriority.CRITICAL

    def to_maven_test(self) -> str:
        """转换为Maven测试格式."""
        return f"{self.class_name}#{self.method_name}"

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "class_name": self.class_name,
            "method_name": self.method_name,
            "full_name": self.full_name,
            "test_type": self.test_type.value,
            "priority": self.priority.value,
            "target_class": self.target_class,
            "target_method": self.target_method,
            "file_path": str(self.file_path) if self.file_path else None,
            "line_number": self.line_number,
            "tags": self.tags,
        }


@dataclass
class TestSuite:
    """测试套件.

    Attributes:
        name: 套件名称
        test_cases: 测试用例列表
        description: 描述
    """

    name: str
    test_cases: list[TestCase] = field(default_factory=list)
    description: str | None = None

    @property
    def test_count(self) -> int:
        """测试数量."""
        return len(self.test_cases)

    @property
    def critical_tests(self) -> list[TestCase]:
        """关键测试列表."""
        return [tc for tc in self.test_cases if tc.is_critical]

    @property
    def generated_tests(self) -> list[TestCase]:
        """自动生成的测试列表."""
        return [tc for tc in self.test_cases if tc.is_generated]

    def add_test(self, test_case: TestCase) -> None:
        """添加测试用例."""
        self.test_cases.append(test_case)

    def filter_by_priority(self, priority: TestPriority) -> list[TestCase]:
        """按优先级过滤."""
        return [tc for tc in self.test_cases if tc.priority == priority]

    def filter_by_tag(self, tag: str) -> list[TestCase]:
        """按标签过滤."""
        return [tc for tc in self.test_cases if tag in tc.tags]

    def to_maven_test_list(self) -> list[str]:
        """转换为Maven测试列表."""
        return [tc.to_maven_test() for tc in self.test_cases]

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "name": self.name,
            "test_count": self.test_count,
            "description": self.description,
            "test_cases": [tc.to_dict() for tc in self.test_cases],
        }
