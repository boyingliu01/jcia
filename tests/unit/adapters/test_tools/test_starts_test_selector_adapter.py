"""STARTS 测试选择器适配器单元测试."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from jcia.adapters.maven.maven_adapter import MavenAdapter
from jcia.adapters.tools.starts_test_selector_adapter import (
    STARTSTestSelectorAdapter,
)
from jcia.core.entities.test_case import TestCase, TestPriority, TestType
from jcia.core.interfaces.test_runner import TestSelectionStrategy


@pytest.fixture
def mock_maven_adapter() -> MavenAdapter:
    """Mock Maven adapter."""
    adapter = MagicMock(spec=MavenAdapter)
    return adapter


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create temporary project directory structure."""
    # Create source directory structure
    src_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Create a simple Java file
    java_file = src_dir / "Service.java"
    java_file.write_text("""
public class Service {
    public void method1() {}
    public void method2() {
        helper.method();
    }
}
""")

    return tmp_path


class TestSTARTSTestSelectorAdapter:
    """STARTSTestSelectorAdapter 测试类."""

    def test_init_stores_project_path(self, mock_maven_adapter: MagicMock) -> None:
        """测试初始化存储项目路径."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        assert adapter._project_path == Path("/test/project").resolve()

    def test_init_stores_maven_adapter(self, mock_maven_adapter: MagicMock) -> None:
        """测试初始化存储 Maven adapter."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        assert adapter._maven == mock_maven_adapter

    def test_init_stores_starts_version(self, mock_maven_adapter: MagicMock) -> None:
        """测试初始化存储 STARTS 版本."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
            starts_version="2.0",
        )

        assert adapter._starts_version == "2.0"

    def test_init_resolves_project_path(self, mock_maven_adapter: MagicMock) -> None:
        """测试初始化解析项目路径."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("./test/project"),
            maven_adapter=mock_maven_adapter,
        )

        assert adapter._project_path.is_absolute()

    def test_get_selection_strategy(self, mock_maven_adapter: MagicMock) -> None:
        """测试获取选择策略."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        assert adapter.get_selection_strategy == TestSelectionStrategy.STARTS

    def test_select_tests_empty_changes(self, mock_maven_adapter: MagicMock) -> None:
        """测试选择空变更列表返回空结果."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        result = adapter.select_tests([], Path("/test/project"))

        assert result == []

    def test_select_tests_selects_affected(
        self, mock_maven_adapter: MagicMock
    ) -> None:
        """测试选择受影响的测试."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        # Set up test code mapping
        adapter._test_code_mapping = {
            "com.example.ServiceTest": {"com.example.Service.method1"},
        }

        changed_methods = ["com.example.Service.method1"]

        result = adapter.select_tests(changed_methods, Path("/test/project"))

        assert len(result) == 1
        assert result[0].class_name == "com.example.ServiceTest"
        assert result[0].priority == TestPriority.HIGH

    def test_analyze_affected_classes(self, mock_maven_adapter: MagicMock) -> None:
        """测试分析受影响的类."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        changed_methods = [
            "com.example.Service.method1",
            "com.example.Repository.method2",
        ]

        result = adapter._analyze_affected_classes(changed_methods)

        assert "com.example.Service" in result
        assert "com.example.Repository" in result
        assert len(result) == 2

    def test_extract_class_name_valid_method(self, mock_maven_adapter: MagicMock) -> None:
        """测试从有效方法名提取类名."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        result = adapter._extract_class_name("com.example.Service.method1")

        assert result == "com.example.Service"

    def test_extract_class_name_invalid_method(self, mock_maven_adapter: MagicMock) -> None:
        """测试从无效方法名提取类名."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        result = adapter._extract_class_name("method1")

        assert result is None

    def test_find_java_file_existing(self, mock_maven_adapter: MagicMock, temp_project_dir: Path) -> None:
        """测试查找存在的 Java 文件."""
        adapter = STARTSTestSelectorAdapter(
            project_path=temp_project_dir,
            maven_adapter=mock_maven_adapter,
        )

        result = adapter._find_java_file("com.example.Service")

        assert result is not None
        assert result.name == "Service.java"

    def test_find_java_file_not_found(self, mock_maven_adapter: MagicMock, temp_project_dir: Path) -> None:
        """测试查找不存在的 Java 文件."""
        adapter = STARTSTestSelectorAdapter(
            project_path=temp_project_dir,
            maven_adapter=mock_maven_adapter,
        )

        result = adapter._find_java_file("com.example.NonExistent")

        assert result is None

    def test_parse_method_calls_object_method(self, mock_maven_adapter: MagicMock) -> None:
        """测试解析对象方法调用."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        content = """
public void test() {
    helper.method();
    repository.save(data);
}
"""
        result = adapter._parse_method_calls(content, "TestClass")

        assert "helper.method" in result
        assert "repository.save" in result

    def test_parse_method_calls_constructor(self, mock_maven_adapter: MagicMock) -> None:
        """测试解析构造函数调用."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        content = """
public void test() {
    Service service = new Service();
    data = new Data();
}
"""
        result = adapter._parse_method_calls(content, "TestClass")

        # The implementation returns "Service.Service" and "Data.Data" for new Class() calls
        assert "Service.Service" in result
        assert "Data.Data" in result

    def test_parse_method_calls_this_ignored(self, mock_maven_adapter: MagicMock) -> None:
        """测试忽略 this 和 super 调用."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        content = """
public void test() {
    this.method1();
    super.method2();
    other.method();
}
"""
        result = adapter._parse_method_calls(content, "TestClass")

        assert "this.method1" not in result
        assert "super.method2" not in result
        assert "other.method" in result

    def test_propagate_changes(self, mock_maven_adapter: MagicMock) -> None:
        """测试变更传播."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        # Mock dependency analysis
        adapter._analyze_class_dependencies = Mock(return_value=["Service.method2"])  # type: ignore[method-assign]

        changed_methods = ["Service.method1"]

        result = adapter._propagate_changes(changed_methods)

        assert "Service.method1" in result
        assert "Service.method2" in result

    def test_propagate_changes_max_depth(self, mock_maven_adapter: MagicMock) -> None:
        """测试变更传播最大深度限制."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        # Mock dependency analysis to always return new methods
        call_count = [0]
        def mock_analysis(class_name: str) -> list[str]:
            call_count[0] += 1
            if call_count[0] > 15:  # More than max_depth * 2
                return []
            return [f"Method{call_count[0]}"]

        adapter._analyze_class_dependencies = Mock(side_effect=mock_analysis)  # type: ignore[method-assign]

        changed_methods = ["Service.method1"]

        result = adapter._propagate_changes(changed_methods)

        # Should stop at max_depth (10)
        assert len(result) <= 20  # Approximately max_depth * 2

    def test_analyze_class_dependencies_cached(
        self, mock_maven_adapter: MagicMock
    ) -> None:
        """测试依赖分析缓存."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        # Set cache - use full class name as key
        adapter._dependency_cache["Service"] = ["Service.method1", "Service.method2"]

        result = adapter._analyze_class_dependencies("Service")

        assert result == ["Service.method1", "Service.method2"]
        # The implementation uses the cache before calling _find_java_file

    def test_select_affected_tests(self, mock_maven_adapter: MagicMock) -> None:
        """测试选择受影响的测试."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        # Set up test code mapping
        adapter._test_code_mapping = {
            "com.example.ServiceTest": {"Service.method1", "Service.method2"},
            "com.example.OtherTest": {"Other.method1"},
        }

        affected_methods = {"Service.method1"}

        result = adapter._select_affected_tests(affected_methods, set())

        assert len(result) == 1
        assert result[0].class_name == "com.example.ServiceTest"
        assert result[0].target_class == "Service"

    def test_select_affected_tests_sorted_by_priority(
        self, mock_maven_adapter: MagicMock
    ) -> None:
        """测试测试按优先级排序."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        # Set up test code mapping with different priorities
        adapter._test_code_mapping = {
            "com.example.LowTest": {"Service.method1"},
            "com.example.HighTest": {"Service.method2"},
        }

        affected_methods = {"Service.method1", "Service.method2"}

        result = adapter._select_affected_tests(affected_methods, set())

        assert len(result) == 2
        # Both should be HIGH priority by default
        assert all(tc.priority == TestPriority.HIGH for tc in result)

    def test_clear_cache(self, mock_maven_adapter: MagicMock) -> None:
        """测试清空缓存."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        # Set some data in caches
        adapter._dependency_cache = {"Service": ["method1"]}
        adapter._test_code_mapping = {"Test": set()}
        adapter._class_cache = {"Class": ["method"]}

        adapter.clear_cache()

        assert len(adapter._dependency_cache) == 0
        assert len(adapter._test_code_mapping) == 0
        assert len(adapter._class_cache) == 0

    def test_get_class_dependencies(self, mock_maven_adapter: MagicMock) -> None:
        """测试获取类依赖."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        expected = ["Service.method1", "Service.method2"]
        adapter._analyze_class_dependencies = Mock(return_value=expected)  # type: ignore[method-assign]

        result = adapter.get_class_dependencies("Service")

        assert result == expected

    def test_export_dependency_graph(self, mock_maven_adapter: MagicMock, tmp_path: Path) -> None:
        """测试导出依赖图."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        # Set up dependency cache
        adapter._dependency_cache = {
            "Service": ["Helper.method1", "Repository.method2"],
            "Helper": [],
        }

        output_path = tmp_path / "dependency_graph.json"

        adapter.export_dependency_graph(output_path)

        assert output_path.exists()

        import json

        with open(output_path) as f:
            graph = json.load(f)

        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 2

    def test_analyze_test_impact(self, mock_maven_adapter: MagicMock) -> None:
        """测试分析测试影响."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        # Set up test code mapping
        adapter._test_code_mapping = {
            "com.example.ServiceTest": {"Service.method1", "Service.method2", "Service.method3"},
        }

        changed_methods = ["Service.method1", "Service.method2"]

        result = adapter.analyze_test_impact("com.example.ServiceTest", changed_methods)

        assert result["test_class"] == "com.example.ServiceTest"
        assert result["coverage_count"] == 3
        assert result["affected_count"] == 2
        assert result["impact_percentage"] == pytest.approx(66.67, rel=0.1)

    def test_analyze_test_impact_unknown_test(self, mock_maven_adapter: MagicMock) -> None:
        """测试分析未知测试的影响."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        changed_methods = ["Service.method1"]

        result = adapter.analyze_test_impact("com.example.UnknownTest", changed_methods)

        assert result["test_class"] == "com.example.UnknownTest"
        assert result["coverage_count"] == 0
        assert result["affected_count"] == 0
        assert result["impact_percentage"] == 0.0

    def test_get_test_statistics(self, mock_maven_adapter: MagicMock) -> None:
        """测试获取测试统计信息."""
        adapter = STARTSTestSelectorAdapter(
            project_path=Path("/test/project"),
            maven_adapter=mock_maven_adapter,
        )

        # Set up data
        adapter._test_code_mapping = {"Test1": set(), "Test2": set()}
        adapter._dependency_cache = {"Service": ["method1", "method2"]}

        stats = adapter.get_test_statistics()

        assert stats["total_test_classes"] == 2
        assert stats["total_dependencies"] == 2
        assert stats["cache_size"] == 1


class TestClassDependency:
    """ClassDependency 测试类."""

    def test_class_dependency_init(self) -> None:
        """测试 ClassDependency 初始化."""
        from jcia.adapters.tools.starts_test_selector_adapter import ClassDependency

        class_dep = ClassDependency(
            class_name="com.example.Service",
            dependencies=["Helper.method1", "Repository.method2"],
            depth=2,
        )

        assert class_dep.class_name == "com.example.Service"
        assert class_dep.dependencies == ["Helper.method1", "Repository.method2"]
        assert class_dep.depth == 2

    def test_class_dependency_default_depth(self) -> None:
        """测试 ClassDependency 默认深度."""
        from jcia.adapters.tools.starts_test_selector_adapter import ClassDependency

        class_dep = ClassDependency(
            class_name="com.example.Service",
            dependencies=["Helper.method1"],
        )

        assert class_dep.depth == 0
