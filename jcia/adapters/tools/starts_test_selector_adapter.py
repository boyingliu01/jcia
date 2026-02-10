"""STARTS 测试选择器适配器实现.

基于 STARTS (Static Test Assignment for Regression Test Selection) 算法的测试选择器。
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from defusedxml import ElementTree as ET
from jcia.adapters.maven.maven_adapter import MavenAdapter
from jcia.core.entities.test_case import TestCase, TestPriority, TestType
from jcia.core.interfaces.test_runner import TestSelectionStrategy

logger = logging.getLogger(__name__)

# 常量定义
STARTS_VERSION = "1.4"
STARTS_GROUP_ID = "edu.illinois"
STARTS_ARTIFACT_ID = "starts-maven-plugin"


@dataclass
class ClassDependency:
    """类依赖信息."""

    class_name: str
    dependencies: list[str]
    depth: int = 0


class STARTSTestSelectorAdapter:
    """STARTS 测试选择器适配器.

    使用 STARTS 算法基于类级别依赖关系选择测试用例：
    - 增量测试选择
    - 测试-代码映射
    - 变更传播分析
    """

    def __init__(
        self,
        project_path: Path,
        maven_adapter: MavenAdapter,
        starts_version: str = STARTS_VERSION,
    ) -> None:
        """初始化测试选择器.

        Args:
            project_path: Maven 项目路径
            maven_adapter: Maven 适配器
            starts_version: STARTS 版本
        """
        self._project_path = Path(project_path).resolve()
        self._maven = maven_adapter
        self._starts_version = starts_version

        # 缓存
        self._dependency_cache: dict[str, list[str]] = {}
        self._test_code_mapping: dict[str, set[str]] = {}
        self._class_cache: dict[str, list[str]] = {}

        logger.info(
            f"STARTSTestSelectorAdapter initialized for project: {self._project_path}"
        )

    @property
    def get_selection_strategy(self) -> TestSelectionStrategy:
        """获取选择策略."""
        return TestSelectionStrategy.STARTS

    def select_tests(
        self, changed_methods: list[str], project_path: Path, **kwargs: Any
    ) -> list[TestCase]:
        """选择需要执行的测试用例.

        Args:
            changed_methods: 变更的方法列表
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            List[TestCase]: 选中的测试用例列表
        """
        logger.info(f"Selecting tests for {len(changed_methods)} changed methods")

        if not changed_methods:
            logger.warning("No changed methods provided")
            return []

        # 1. 构建测试-代码映射
        self._build_test_code_mapping()

        # 2. 分析类依赖
        affected_classes = self._analyze_affected_classes(changed_methods)

        # 3. 传播变更影响
        all_affected = self._propagate_changes(changed_methods)

        # 4. 选择受影响的测试
        selected_tests = self._select_affected_tests(
            all_affected, affected_classes
        )

        logger.info(f"Selected {len(selected_tests)} affected tests")

        return selected_tests

    def _build_test_code_mapping(self) -> dict[str, set[str]]:
        """构建测试到代码的映射关系.

        Returns:
            Dict[str, set[str]]: 测试到代码方法的映射
        """
        if self._test_code_mapping:
            return self._test_code_mapping

        logger.info("Building test-to-code mapping")

        # 执行测试并收集覆盖率
        self._run_tests_for_mapping()

        # 解析 JaCoCo XML 报告
        jacoco_xml = self._project_path / "target" / "site" / "jacoco" / "jacoco.xml"

        if jacoco_xml.exists():
            tree = ET.parse(jacoco_xml)
            root = tree.getroot()

            # 遍历所有包和类
            for package in root.findall(".//package"):
                package_name = package.get("name")

                for class_elem in package.findall(".//class"):
                    class_name = class_elem.get("name").replace("/", ".")

                    # 找到覆盖这个类的测试
                    for method in class_elem.findall(".//method"):
                        # 从类名推断测试类名
                        simple_name = class_name.split(".")[-1]
                        test_name = f"{package_name}.{simple_name}Test"

                        if test_name not in self._test_code_mapping:
                            self._test_code_mapping[test_name] = set()

                        # 添加方法到测试映射
                        method_full = f"{class_name}.{method.get('name')}"
                        self._test_code_mapping[test_name].add(method_full)

            logger.info(
                f"Built mapping for {len(self._test_code_mapping)} test classes"
            )

        return self._test_code_mapping

    def _run_tests_for_mapping(self) -> None:
        """运行测试以收集覆盖率."""
        logger.info("Running tests to collect coverage data")

        cmd = ["mvn", "clean", "test", "jacoco:report", "-q"]

        result = self._maven.execute(args=cmd)

        if not result.success:
            logger.warning(f"Test execution for mapping had issues: {result.stderr}")

    def _analyze_affected_classes(self, changed_methods: list[str]) -> set[str]:
        """分析受影响的类.

        Args:
            changed_methods: 变更的方法列表

        Returns:
            Set[str]: 受影响的类集合
        """
        affected_classes = set()

        for method in changed_methods:
            # 从方法全限定名提取类名
            parts = method.split(".")
            if len(parts) >= 2:
                class_name = ".".join(parts[:-1])
                affected_classes.add(class_name)

        return affected_classes

    def _propagate_changes(self, changed_methods: list[str]) -> set[str]:
        """传播变更影响（STARTS 算法核心）.

        Args:
            changed_methods: 变更的方法列表

        Returns:
            Set[str]: 所有受影响的方法
        """
        affected = set(changed_methods)
        work_queue = list(changed_methods)
        max_depth = 10
        depth = 0

        logger.info(f"Propagating changes with max depth: {max_depth}")

        while work_queue and depth < max_depth:
            next_queue = []

            for method in work_queue:
                # 提取类名
                class_name = self._extract_class_name(method)

                if not class_name:
                    continue

                # 分析类依赖
                dependencies = self._analyze_class_dependencies(class_name)

                for dep in dependencies:
                    if dep not in affected:
                        affected.add(dep)
                        next_queue.append(dep)

            work_queue = next_queue
            depth += 1

        logger.info(f"Change propagation completed: {len(affected)} affected methods")

        return affected

    def _analyze_class_dependencies(self, class_name: str) -> list[str]:
        """分析类依赖（增量）.

        Args:
            class_name: 类名

        Returns:
            List[str]: 依赖的方法列表
        """
        if class_name in self._dependency_cache:
            return self._dependency_cache[class_name]

        # 查找 Java 文件
        java_file = self._find_java_file(class_name)

        if not java_file:
            return []

        # 解析源代码提取方法调用
        try:
            content = java_file.read_text(encoding="utf-8", errors="ignore")
            dependencies = self._parse_method_calls(content, class_name)

            self._dependency_cache[class_name] = dependencies
            return dependencies

        except Exception as e:
            logger.warning(f"Failed to analyze dependencies for {class_name}: {e}")
            return []

    def _find_java_file(self, class_name: str) -> Path | None:
        """查找 Java 源文件.

        Args:
            class_name: 类名

        Returns:
            Path | None: Java 文件路径
        """
        # 转换为文件路径
        path_parts = class_name.split(".")
        file_name = f"{path_parts[-1]}.java"
        dir_path = self._project_path.joinpath(*path_parts[:-1])

        java_file = dir_path / file_name
        if java_file.exists():
            return java_file

        # 在项目中搜索
        for java_path in self._project_path.rglob(f"{file_name}"):
            return java_path

        return None

    def _parse_method_calls(self, content: str, class_name: str) -> list[str]:
        """解析方法调用.

        Args:
            content: Java 源代码
            class_name: 类名

        Returns:
            List[str]: 调用的方法列表
        """
        calls = []

        # 匹配方法调用模式
        # 简化的正则表达式，实际应用可能需要更复杂的解析
        patterns = [
            r'(\w+)\.(\w+)\s*\(',  # object.method()
            r'\bnew\s+(\w+)\s*\(',  # new Constructor()
            r'\b(\w+)\s*\(',  # method()
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                object_name = match.group(1) if match.lastindex >= 1 else ""
                method_name = match.group(2) if match.lastindex >= 2 else match.group(1)

                # 忽略内置类和this调用
                if object_name in ["this", "super"]:
                    continue

                # 构建方法全限定名（简化）
                if object_name:
                    full_method = f"{object_name}.{method_name}"
                else:
                    full_method = f"{class_name}.{method_name}"

                if full_method not in calls:
                    calls.append(full_method)

        return calls

    def _extract_class_name(self, method: str) -> str | None:
        """从方法全限定名提取类名.

        Args:
            method: 方法全限定名

        Returns:
            str | None: 类名
        """
        parts = method.split(".")
        if len(parts) >= 2:
            return ".".join(parts[:-1])
        return None

    def _select_affected_tests(
        self, affected_methods: set[str], affected_classes: set[str]
    ) -> list[TestCase]:
        """选择受影响的测试.

        Args:
            affected_methods: 受影响的方法集合
            affected_classes: 受影响的类集合

        Returns:
            List[TestCase]: 选中的测试用例列表
        """
        selected = []

        # 遍历测试-代码映射
        for test_class, covered_methods in self._test_code_mapping.items():
            # 检查测试是否覆盖任何受影响的方法
            if not covered_methods.isdisjoint(affected_methods):
                # 从测试类名提取目标类
                simple_name = test_class.split(".")[-1]
                target_class = simple_name.replace("Test", "")

                test_case = TestCase(
                    class_name=test_class,
                    method_name=None,  # 不指定方法名，运行整个测试类
                    test_type=TestType.UNIT,
                    priority=TestPriority.HIGH,
                    target_class=target_class,
                    target_method=None,
                    metadata={"selection_reason": "covers_affected_code"},
                )

                selected.append(test_case)

        # 按优先级排序
        selected.sort(key=lambda tc: tc.priority.value, reverse=True)

        return selected

    def get_class_dependencies(self, class_name: str) -> list[str]:
        """获取类的依赖关系.

        Args:
            class_name: 类名

        Returns:
            List[str]: 依赖的类列表
        """
        return self._analyze_class_dependencies(class_name)

    def clear_cache(self) -> None:
        """清空缓存."""
        self._dependency_cache.clear()
        self._test_code_mapping.clear()
        self._class_cache.clear()
        logger.info("Cache cleared")

    def export_dependency_graph(self, output_path: Path) -> None:
        """导出依赖图到文件.

        Args:
            output_path: 输出文件路径
        """
        graph = {"nodes": [], "edges": []}

        # 添加节点
        for class_name in self._dependency_cache:
            graph["nodes"].append({"id": class_name, "name": class_name})

        # 添加边
        for class_name, dependencies in self._dependency_cache.items():
            for dep in dependencies:
                dep_class = self._extract_class_name(dep)
                if dep_class:
                    graph["edges"].append(
                        {"source": class_name, "target": dep_class}
                    )

        # 写入文件
        with open(output_path, "w") as f:
            json.dump(graph, f, indent=2)

        logger.info(f"Dependency graph exported to {output_path}")

    def analyze_test_impact(
        self, test_class: str, changed_methods: list[str]
    ) -> dict[str, Any]:
        """分析测试对变更的影响.

        Args:
            test_class: 测试类名
            changed_methods: 变更的方法列表

        Returns:
            Dict[str, Any]: 影响分析结果
        """
        if test_class not in self._test_code_mapping:
            return {
                "test_class": test_class,
                "coverage_count": 0,
                "affected_count": 0,
                "impact_percentage": 0.0,
            }

        covered_methods = self._test_code_mapping[test_class]
        affected_set = set(changed_methods)
        intersection = covered_methods & affected_set

        return {
            "test_class": test_class,
            "coverage_count": len(covered_methods),
            "affected_count": len(intersection),
            "impact_percentage": (
                len(intersection) / len(covered_methods) * 100
                if covered_methods
                else 0.0
            ),
        }

    def get_test_statistics(self) -> dict[str, Any]:
        """获取测试统计信息.

        Returns:
            Dict[str, Any]: 测试统计数据
        """
        return {
            "total_test_classes": len(self._test_code_mapping),
            "total_dependencies": sum(len(deps) for deps in self._dependency_cache.values()),
            "cache_size": len(self._dependency_cache),
        }
