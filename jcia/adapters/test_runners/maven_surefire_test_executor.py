"""Maven Surefire 测试执行器实现.

基于 Maven Surefire Plugin 的测试执行器，支持选择性测试执行和覆盖率收集。
"""
# ruff: noqa: N817  # defusedxml.ElementTree is official import style

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET

from jcia.adapters.maven.maven_adapter import MavenAdapter
from jcia.core.entities.test_case import TestCase, TestType
from jcia.core.entities.test_run import TestStatus
from jcia.core.interfaces.test_runner import (
    TestExecutionResult,
    TestExecutor,
    TestSuiteResult,
)

logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_SUREFIRE_VERSION = "2.22.2"
DEFAULT_JACOCO_VERSION = "0.8.11"


@dataclass
class TestMethodInfo:
    """测试方法信息."""

    class_name: str
    method_name: str
    full_name: str


class MavenSurefireTestExecutor(TestExecutor):
    """Maven Surefire 测试执行器.

    使用 Maven Surefire Plugin 执行单元测试，支持：
    - 选择性测试执行
    - JaCoCo 覆盖率收集
    - 测试结果解析
    - 增量测试
    """

    def __init__(
        self,
        project_path: Path,
        maven_adapter: MavenAdapter,
        surefire_version: str = DEFAULT_SUREFIRE_VERSION,
        jacoco_version: str = DEFAULT_JACOCO_VERSION,
    ) -> None:
        """初始化测试执行器.

        Args:
            project_path: Maven 项目路径
            maven_adapter: Maven 适配器
            surefire_version: Surefire 插件版本
            jacoco_version: JaCoCo 插件版本
        """
        self._project_path = Path(project_path).resolve()
        self._maven = maven_adapter
        self._surefire_version = surefire_version
        self._jacoco_version = jacoco_version

        # 报告目录
        self._surefire_reports = self._project_path / "target" / "surefire-reports"
        self._failsafe_reports = self._project_path / "target" / "failsafe-reports"
        self._jacoco_reports = self._project_path / "target" / "site" / "jacoco"

        logger.info(
            f"MavenSurefireTestExecutor initialized for project: {self._project_path}"
        )

    def execute_tests(
        self,
        test_cases: list[TestCase] | None = None,
        project_path: Path | None = None,
        **kwargs: Any,
    ) -> TestSuiteResult:
        """执行测试.

        Args:
            test_cases: 要执行的测试用例（None 则执行所有）
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            TestSuiteResult: 测试结果
        """
        if not test_cases:
            # 执行所有测试
            logger.info("Executing all tests")
            return self._run_all_tests(**kwargs)

        # 执行选定的测试
        logger.info(f"Executing {len(test_cases)} selected tests")
        return self._run_selected_tests(test_cases, **kwargs)

    def execute_with_coverage(
        self,
        test_cases: list[TestCase] | None = None,
        project_path: Path | None = None,
        **kwargs: Any,
    ) -> TestSuiteResult:
        """执行测试并收集覆盖率.

        Args:
            test_cases: 要执行的测试用例
            project_path: 项目路径
            **kwargs: 额外参数

        Returns:
            TestSuiteResult: 包含覆盖率的测试结果
        """
        logger.info("Executing tests with coverage")

        # 配置 JaCoCo
        self._configure_jacoco()

        # 执行测试
        result = self.execute_tests(test_cases, project_path, with_coverage=True, **kwargs)

        # 解析覆盖率数据
        coverage_data = self._parse_jacoco_coverage()
        result.coverage_percent = coverage_data.get("line_coverage", 0.0)

        logger.info(f"Coverage: {result.coverage_percent:.2f}%")

        return result

    def get_coverage_report(
        self, project_path: Path, report_format: str = "xml"
    ) -> dict[str, Any]:
        """获取覆盖率报告.

        Args:
            project_path: 项目路径
            report_format: 报告格式（xml/html/csv）

        Returns:
            Dict[str, Any]: 覆盖率数据
        """
        # 执行测试以生成覆盖率报告
        result = self.execute_with_coverage(project_path=project_path)

        return {
            "line_coverage": result.coverage_percent,
            "total_tests": result.total_tests,
            "passed_tests": result.passed_tests,
            "failed_tests": result.failed_tests,
        }

    def _run_all_tests(self, **kwargs: Any) -> TestSuiteResult:
        """运行所有测试.

        Args:
            **kwargs: 额外参数

        Returns:
            TestSuiteResult: 测试结果
        """
        cmd = ["mvn", "clean", "test"]

        # 添加覆盖率
        if kwargs.get("with_coverage", False):
            cmd.insert(-1, "jacoco:prepare-agent")
            cmd.insert(-1, "jacoco:report")

        # 添加其他参数
        if kwargs.get("skip_tests", False):
            cmd.append("-DskipTests")

        if kwargs.get("fail_fast", False):
            cmd.append("-DfailFast")

        # 执行 Maven 命令
        result = self._maven.execute(args=cmd)

        if not result.success:
            logger.error(f"Maven test execution failed: {result.stderr}")

        # 解析测试结果
        return self._parse_test_results()

    def _run_selected_tests(self, test_cases: list[TestCase], **kwargs: Any) -> TestSuiteResult:
        """运行选定的测试.

        Args:
            test_cases: 测试用例列表
            **kwargs: 额外参数

        Returns:
            TestSuiteResult: 测试结果
        """
        # 构建测试模式
        test_pattern = self._build_test_pattern(test_cases)

        cmd = ["mvn", "surefire:test", f"-Dtest={test_pattern}", "-DfailIfNoTests=false"]

        # 添加覆盖率
        if kwargs.get("with_coverage", False):
            cmd.insert(-1, "jacoco:prepare-agent")
            cmd.insert(-1, "jacoco:report")

        # 添加其他参数
        if kwargs.get("fail_fast", False):
            cmd.append("-DfailFast")

        logger.debug(f"Executing tests with pattern: {test_pattern}")

        # 执行 Maven 命令
        result = self._maven.execute(args=cmd)

        if not result.success:
            logger.warning(f"Maven test execution had issues: {result.stderr}")

        # 解析测试结果
        return self._parse_test_results()

    def _build_test_pattern(self, test_cases: list[TestCase]) -> str:
        """构建 Maven 测试模式.

        Args:
            test_cases: 测试用例列表

        Returns:
            str: Maven 测试模式
        """
        patterns = []

        for tc in test_cases:
            # 提取简单类名
            simple_class = tc.class_name.split(".")[-1]

            # Surefire 模式: TestClass#testMethod
            if tc.method_name:
                patterns.append(f"{simple_class}#{tc.method_name}")
            else:
                patterns.append(f"{simple_class}")

        # 用逗号连接多个测试
        return ",".join(patterns)

    def _parse_test_results(self) -> TestSuiteResult:
        """解析测试结果.

        Returns:
            TestSuiteResult: 测试结果
        """
        result = TestSuiteResult()

        # 解析 Surefire 报告
        if self._surefire_reports.exists():
            for xml_file in self._surefire_reports.glob("TEST-*.xml"):
                test_suite = self._parse_test_suite_xml(xml_file)

                result.total_tests += test_suite["total"]
                result.passed_tests += test_suite["passed"]
                result.failed_tests += test_suite["failed"]
                result.skipped_tests += test_suite["skipped"]
                result.error_tests += test_suite["errors"]
                result.total_duration_ms += test_suite["duration"]

                result.test_results.extend(test_suite["cases"])

        # 解析 Failsafe 报告（集成测试）
        if self._failsafe_reports.exists():
            for xml_file in self._failsafe_reports.glob("TEST-*.xml"):
                test_suite = self._parse_test_suite_xml(xml_file)

                result.total_tests += test_suite["total"]
                result.passed_tests += test_suite["passed"]
                result.failed_tests += test_suite["failed"]
                result.skipped_tests += test_suite["skipped"]
                result.error_tests += test_suite["errors"]
                result.total_duration_ms += test_suite["duration"]

                result.test_results.extend(test_suite["cases"])

        logger.info(
            f"Test results: {result.passed_tests} passed, "
            f"{result.failed_tests} failed, "
            f"{result.skipped_tests} skipped, "
            f"{result.error_tests} errors"
        )

        return result

    def _parse_test_suite_xml(self, xml_path: Path) -> dict:
        """解析单个测试套件 XML.

        Args:
            xml_path: XML 文件路径

        Returns:
            Dict[str, Any]: 测试套件数据
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            test_suite = {
                "total": int(root.get("tests", 0)),
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0,
                "duration": int(float(root.get("time", 0)) * 1000),
                "cases": [],
            }

            for test_case in root.findall("testcase"):
                case = self._parse_test_case(test_case)
                test_suite["cases"].append(case)

                if case["status"] == TestStatus.PASSED:
                    test_suite["passed"] += 1
                elif case["status"] == TestStatus.FAILED:
                    test_suite["failed"] += 1
                elif case["status"] == TestStatus.SKIPPED:
                    test_suite["skipped"] += 1
                elif case["status"] == TestStatus.ERROR:
                    test_suite["errors"] += 1

            return test_suite

        except Exception as e:
            logger.error(f"Failed to parse test suite XML {xml_path}: {e}")
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0,
                "duration": 0,
                "cases": [],
            }

    def _parse_test_case(self, element) -> dict:
        """解析单个测试用例.

        Args:
            element: XML 元素

        Returns:
            Dict[str, Any]: 测试用例数据
        """
        class_name = element.get("classname", "")
        method_name = element.get("name", "")
        duration = int(float(element.get("time", 0)) * 1000)

        # 查找失败/错误信息
        failure = element.find("failure")
        error = element.find("error")

        if failure is not None:
            status = TestStatus.FAILED
            error_message = failure.get("message", "")
            stack_trace = failure.text or ""
        elif error is not None:
            status = TestStatus.ERROR
            error_message = error.get("message", "")
            stack_trace = error.text or ""
        elif element.find("skipped") is not None:
            status = TestStatus.SKIPPED
            error_message = None
            stack_trace = None
        else:
            status = TestStatus.PASSED
            error_message = None
            stack_trace = None

        return TestExecutionResult(
            test_class=class_name,
            test_method=method_name,
            status=status,
            duration_ms=duration,
            error_message=error_message,
            stack_trace=stack_trace,
        )

    def _configure_jacoco(self) -> None:
        """配置 JaCoCo 插件.

        检查并添加 JaCoCo 插件到 pom.xml。
        """
        pom_path = self._project_path / "pom.xml"

        if not pom_path.exists():
            logger.warning(f"pom.xml not found at {pom_path}")
            return

        # 检查是否已配置 JaCoCo
        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()

            # 定义 JaCoCo 插件配置
            jacoco_plugin = ET.Element("plugin")
            ET.SubElement(jacoco_plugin, "groupId").text = "org.jacoco"
            ET.SubElement(jacoco_plugin, "artifactId").text = "jacoco-maven-plugin"
            ET.SubElement(jacoco_plugin, "version").text = self._jacoco_version

            executions = ET.SubElement(jacoco_plugin, "executions")

            # prepare-agent execution
            execution1 = ET.SubElement(executions, "execution")
            ET.SubElement(execution1, "id").text = "prepare-agent"
            ET.SubElement(execution1, "goals")
            ET.SubElement(execution1, "goals", "goal").text = "prepare-agent"

            # report execution
            execution2 = ET.SubElement(executions, "execution")
            ET.SubElement(execution2, "id").text = "report"
            ET.SubElement(execution2, "phase").text = "test"
            ET.SubElement(execution2, "goals")
            ET.SubElement(execution2, "goals", "goal").text = "report"

            # 检查是否已存在 JaCoCo 插件
            plugins = root.find(".//{*}artifactId[text()='jacoco-maven-plugin']")
            if plugins is None:
                logger.info("JaCoCo plugin not found, would add (implementation note)")

                # 注意：实际实现需要更复杂的 XML 操作
                # 这里只是演示，实际使用时需要完整的 pom.xml 修改逻辑
            else:
                logger.debug("JaCoCo plugin already configured")

        except Exception as e:
            logger.error(f"Failed to configure JaCoCo: {e}")

    def _parse_jacoco_coverage(self) -> dict:
        """解析 JaCoCo 覆盖率数据.

        Returns:
            Dict[str, Any]: 覆盖率数据
        """
        jacoco_xml = self._jacoco_reports / "jacoco.xml"

        if not jacoco_xml.exists():
            logger.warning(f"JaCoCo report not found: {jacoco_xml}")
            return {"line_coverage": 0.0, "total_lines": 0, "covered_lines": 0}

        try:
            tree = ET.parse(jacoco_xml)
            root = tree.getroot()

            total_lines = 0
            covered_lines = 0

            # 遍历所有 counter 元素
            for counter in root.findall(".//counter"):
                if counter.get("type") == "LINE":
                    total_lines += int(counter.get("missed"))
                    total_lines += int(counter.get("covered"))
                    covered_lines += int(counter.get("covered"))

            line_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0.0

            logger.info(
                f"JaCoCo coverage: {covered_lines}/{total_lines} lines ({line_coverage:.2f}%)"
            )

            return {
                "line_coverage": line_coverage,
                "total_lines": total_lines,
                "covered_lines": covered_lines,
            }

        except Exception as e:
            logger.error(f"Failed to parse JaCoCo coverage: {e}")
            return {"line_coverage": 0.0, "total_lines": 0, "covered_lines": 0}

    def execute_incremental_tests(
        self,
        baseline_file: Path,
        changed_methods: list[str],
        **kwargs: Any
    ) -> TestSuiteResult:
        """增量测试执行（仅运行受影响的测试）.

        Args:
            baseline_file: 基线测试结果文件
            changed_methods: 变更的方法列表
            **kwargs: 额外参数

        Returns:
            TestSuiteResult: 测试结果
        """
        # 读取基线测试结果
        baseline = self._load_baseline(baseline_file)

        # 选择受影响的测试
        affected_tests = self._select_affected_tests(
            changed_methods, baseline["test_results"]
        )

        logger.info(f"Running {len(affected_tests)} affected tests (incremental)")

        # 执行受影响的测试
        return self.execute_tests(affected_tests, **kwargs)

    def _load_baseline(self, baseline_file: Path) -> dict:
        """加载基线测试结果.

        Args:
            baseline_file: 基线文件路径

        Returns:
            Dict[str, Any]: 基线数据
        """
        import json

        try:
            with open(baseline_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            return {"test_results": []}

    def _select_affected_tests(
        self, changed_methods: list[str], baseline_tests: list[TestExecutionResult]
    ) -> list[TestCase]:
        """选择受影响的测试.

        Args:
            changed_methods: 变更的方法列表
            baseline_tests: 基线测试结果

        Returns:
            List[TestCase]: 受影响的测试列表
        """
        affected = []

        for test in baseline_tests:
            # 检查测试是否覆盖变更的方法
            if self._is_test_affected(test, changed_methods):
                affected.append(
                    TestCase(
                        class_name=test.test_class,
                        method_name=test.test_method,
                        test_type=TestType.UNIT,
                    )
                )

        return affected

    def _is_test_affected(
        self, test: TestExecutionResult, changed_methods: list[str]
    ) -> bool:
        """判断测试是否受影响.

        Args:
            test: 测试结果
            changed_methods: 变更的方法列表

        Returns:
            bool: 是否受影响
        """
        # 检查测试类名
        test_class = test.test_class.lower()

        for changed_method in changed_methods:
            changed_class = changed_method.split(".")[-1].lower()

            # 如果测试类名包含变更的类名，则受影响
            if changed_class in test_class:
                return True

            # 如果测试方法名匹配变更的方法名
            if changed_method.lower() in f"{test.test_class}.{test.test_method}".lower():
                return True

        return False

    def clean_test_reports(self) -> None:
        """清理测试报告目录."""
        for reports_dir in [self._surefire_reports, self._failsafe_reports, self._jacoco_reports]:
            if reports_dir.exists():
                import shutil

                shutil.rmtree(reports_dir)
                logger.info(f"Cleaned test reports directory: {reports_dir}")
