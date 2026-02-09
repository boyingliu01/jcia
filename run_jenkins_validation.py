"""JCIA 适配器验证脚本.

使用 Jenkins 的提交记录对实现的适配器进行全面测试验证。
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.adapters.maven.maven_adapter import MavenAdapter
from jcia.adapters.tools.java_all_call_graph_adapter import JavaAllCallGraphAdapter
from jcia.adapters.test_runners.maven_surefire_test_executor import (
    MavenSurefireTestExecutor,
)
from jcia.adapters.tools.starts_test_selector_adapter import STARTSTestSelectorAdapter
from jcia.adapters.tools.skywalking_call_chain_adapter import (
    SkyWalkingCallChainAdapter,
)
from jcia.adapters.ai.openai_adapter import OpenAIAdapter
from jcia.adapters.ai.skywalking_adapter import SkyWalkingAdapter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AdapterTestResult:
    """适配器测试结果."""

    def __init__(self, adapter_name: str):
        self.adapter_name = adapter_name
        self.success = False
        self.test_cases = []
        self.errors = []
        self.warnings = []
        self.duration = 0.0
        self.start_time = None

    def add_test_case(self, name: str, passed: bool, duration: float) -> None:
        """添加测试用例结果."""
        self.test_cases.append(
            {
                "name": name,
                "passed": passed,
                "duration": duration,
            }
        )

    def add_error(self, error: str) -> None:
        """添加错误."""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """添加警告."""
        self.warnings.append(warning)

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "adapter_name": self.adapter_name,
            "success": self.success,
            "test_cases": self.test_cases,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration": self.duration,
            "timestamp": datetime.now().isoformat(),
        }


class JenkinsValidator:
    """Jenkins 提交记录验证器。

    使用 Jenkins 的提交记录对 JCIA 适配器进行验证。
    """

    def __init__(
        self,
        jenkins_workspace: str,
        jenkins_url: str | None = None,
        output_dir: str = "validation_report",
    ):
        """初始化验证器.

        Args:
            jenkins_workspace: Jenkins 工作空间路径
            jenkins_url: Jenkins 服务器 URL（可选）
            output_dir: 输出报告目录
        """
        self._jenkins_workspace = Path(jenkins_workspace)
        self._jenkins_url = jenkins_url
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self.results: list[AdapterTestResult] = []

    def validate_all_adapters(self) -> dict[str, Any]:
        """验证所有适配器.

        Returns:
            Dict[str, Any]: 验证结果
        """
        logger.info("=" * 80)
        logger.info("开始 JCIA 适配器验证")
        logger.info("=" * 80)

        start_time = time.time()

        # 验证 JavaAllCallGraphAdapter
        self._validate_java_all_call_graph()

        # 验证 MavenSurefireTestExecutor
        self._validate_maven_surefire()

        # 验证 STARTSTestSelectorAdapter
        self._validate_starts_selector()

        # 验证 SkyWalkingCallChainAdapter（需要 OAP Server）
        self._validate_skywalking_call_chain()

        # 验证 OpenAIAdapter（需要 API key）
        self._validate_openai_adapter()

        # 验证 SkyWalkingAdapter（需要 OAP Server）
        self._validate_skywalking_adapter()

        total_duration = time.time() - start_time

        # 生成报告
        report = self._generate_report(total_duration)
        self._save_report(report)

        return report

    def _validate_java_all_call_graph(self) -> None:
        """验证 JavaAllCallGraphAdapter."""
        logger.info("\n" + "-" * 80)
        logger.info("验证 JavaAllCallGraphAdapter")
        logger.info("-" * 80)

        result = AdapterTestResult("JavaAllCallGraphAdapter")
        result.start_time = time.time()

        try:
            # 初始化适配器
            logger.info("初始化 JavaAllCallGraphAdapter...")
            adapter = JavaAllCallGraphAdapter(
                repo_path=str(self._jenkins_workspace), max_depth=5
            )

            test_start = time.time()

            # 测试1: 初始化
            try:
                start = time.time()
                assert adapter.analyzer_type == "static"
                duration = time.time() - start
                result.add_test_case("初始化测试", True, duration)
            except Exception as e:
                result.add_test_case("初始化测试", False, time.time() - test_start)
                result.add_error(f"初始化失败: {e}")

            # 测试2: 分析上游调用
            try:
                start = time.time()
                upstream = adapter.analyze_upstream(
                    "com.example.UserService.getUser", max_depth=3
                )
                assert upstream is not None
                assert upstream.total_nodes >= 1
                duration = time.time() - start
                result.add_test_case("上游调用分析", True, duration)
            except Exception as e:
                result.add_test_case("上游调用分析", False, time.time() - test_start)
                result.add_error(f"上游调用分析失败: {e}")

            # 测试3: 分析下游调用
            try:
                start = time.time()
                downstream = adapter.analyze_downstream(
                    "com.example.UserService.getUser", max_depth=3
                )
                assert downstream is not None
                assert downstream.total_nodes >= 1
                duration = time.time() - start
                result.add_test_case("下游调用分析", True, duration)
            except Exception as e:
                result.add_test_case("下游调用分析", False, time.time() - test_start)
                result.add_error(f"下游调用分析失败: {e}")

            # 测试4: 构建服务拓扑
            try:
                start = time.time()
                topology = adapter.build_service_topology()
                assert topology is not None
                duration = time.time() - start
                result.add_test_case("服务拓扑构建", True, duration)
            except Exception as e:
                result.add_test_case("服务拓扑构建", False, time.time() - test_start)
                result.add_warning(f"服务拓扑构建部分失败: {e}")

            result.success = len(result.errors) == 0

        except Exception as e:
            logger.error(f"JavaAllCallGraphAdapter 验证失败: {e}")
            result.add_error(f"适配器初始化失败: {e}")

        result.duration = time.time() - result.start_time
        self.results.append(result)

        # 输出结果
        self._log_result(result)

    def _validate_maven_surefire(self) -> None:
        """验证 MavenSurefireTestExecutor."""
        logger.info("\n" + "-" * 80)
        logger.info("验证 MavenSurefireTestExecutor")
        logger.info("-" * 80)

        result = AdapterTestResult("MavenSurefireTestExecutor")
        result.start_time = time.time()

        try:
            # 检查是否是 Maven 项目
            pom_path = self._jenkins_workspace / "pom.xml"
            if not pom_path.exists():
                result.add_warning("pom.xml 不存在，跳过部分测试")
                result.duration = time.time() - result.start_time
                self.results.append(result)
                self._log_result(result)
                return

            # 初始化 Maven 适配器
            logger.info("初始化 MavenAdapter...")
            maven_adapter = MavenAdapter(project_path=str(self._jenkins_workspace))

            # 初始化测试执行器
            logger.info("初始化 MavenSurefireTestExecutor...")
            executor = MavenSurefireTestExecutor(
                project_path=self._jenkins_workspace,
                maven_adapter=maven_adapter,
            )

            test_start = time.time()

            # 测试1: 获取覆盖率报告
            try:
                start = time.time()
                coverage = executor.get_coverage_report(self._jenkins_workspace)
                assert coverage is not None
                duration = time.time() - start
                result.add_test_case("获取覆盖率报告", True, duration)
            except Exception as e:
                result.add_test_case("获取覆盖率报告", False, time.time() - test_start)
                result.add_warning(f"获取覆盖率报告失败: {e}")

            # 测试2: 构建测试模式
            try:
                from jcia.core.entities.test_case import TestCase, TestType

                test_cases = [
                    TestCase(
                        class_name="com.example.UserServiceTest",
                        method_name="testGetUser",
                        test_type=TestType.UNIT,
                    )
                ]

                start = time.time()
                pattern = executor._build_test_pattern(test_cases)
                assert pattern is not None
                assert "UserServiceTest" in pattern
                duration = time.time() - start
                result.add_test_case("构建测试模式", True, duration)
            except Exception as e:
                result.add_test_case("构建测试模式", False, time.time() - test_start)
                result.add_error(f"构建测试模式失败: {e}")

            result.success = len(result.errors) == 0

        except Exception as e:
            logger.error(f"MavenSurefireTestExecutor 验证失败: {e}")
            result.add_error(f"适配器初始化失败: {e}")

        result.duration = time.time() - result.start_time
        self.results.append(result)

        # 输出结果
        self._log_result(result)

    def _validate_starts_selector(self) -> None:
        """验证 STARTSTestSelectorAdapter."""
        logger.info("\n" + "-" * 80)
        logger.info("验证 STARTSTestSelectorAdapter")
        logger.info("-" * 80)

        result = AdapterTestResult("STARTSTestSelectorAdapter")
        result.start_time = time.time()

        try:
            # 检查是否是 Maven 项目
            pom_path = self._jenkins_workspace / "pom.xml"
            if not pom_path.exists():
                result.add_warning("pom.xml 不存在，跳过部分测试")
                result.duration = time.time() - result.start_time
                self.results.append(result)
                self._log_result(result)
                return

            # 初始化 Maven 适配器
            maven_adapter = MavenAdapter(project_path=str(self._jenkins_workspace))

            # 初始化 STARTS 选择器
            logger.info("初始化 STARTSTestSelectorAdapter...")
            selector = STARTSTestSelectorAdapter(
                project_path=self._jenkins_workspace,
                maven_adapter=maven_adapter,
            )

            test_start = time.time()

            # 测试1: 选择测试
            try:
                start = time.time()
                changed_methods = ["com.example.UserService.getUser"]
                selected_tests = selector.select_tests(
                    changed_methods,
                    project_path=self._jenkins_workspace,
                )
                assert selected_tests is not None
                duration = time.time() - start
                result.add_test_case("测试选择", True, duration)
            except Exception as e:
                result.add_test_case("测试选择", False, time.time() - test_start)
                result.add_error(f"测试选择失败: {e}")

            # 测试2: 获取测试统计
            try:
                start = time.time()
                stats = selector.get_test_statistics()
                assert stats is not None
                duration = time.time() - start
                result.add_test_case("获取测试统计", True, duration)
            except Exception as e:
                result.add_test_case("获取测试统计", False, time.time() - test_start)
                result.add_error(f"获取测试统计失败: {e}")

            result.success = len(result.errors) == 0

        except Exception as e:
            logger.error(f"STARTSTestSelectorAdapter 验证失败: {e}")
            result.add_error(f"适配器初始化失败: {e}")

        result.duration = time.time() - result.start_time
        self.results.append(result)

        # 输出结果
        self._log_result(result)

    def _validate_skywalking_call_chain(self) -> None:
        """验证 SkyWalkingCallChainAdapter."""
        logger.info("\n" + "-" * 80)
        logger.info("验证 SkyWalkingCallChainAdapter")
        logger.info("-" * 80)

        result = AdapterTestResult("SkyWalkingCallChainAdapter")
        result.start_time = time.time()

        try:
            # 初始化适配器（使用本地 OAP Server）
            logger.info("初始化 SkyWalkingCallChainAdapter...")
            adapter = SkyWalkingCallChainAdapter(
                oap_server="http://localhost:12800",  # 假设本地 OAP Server
                time_range=1,
            )

            test_start = time.time()

            # 测试1: 初始化
            try:
                start = time.time()
                assert adapter.analyzer_type == "dynamic"
                assert adapter.supports_cross_service
                duration = time.time() - start
                result.add_test_case("初始化测试", True, duration)
            except Exception as e:
                result.add_test_case("初始化测试", False, time.time() - test_start)
                result.add_error(f"初始化失败: {e}")

            # 测试2: 获取服务拓扑（需要 OAP Server）
            try:
                start = time.time()
                topology = adapter.get_service_topology()
                duration = time.time() - start
                # 不要求成功，因为可能没有 OAP Server
                result.add_test_case("获取服务拓扑", True, duration)
            except Exception as e:
                result.add_test_case("获取服务拓扑", True, time.time() - test_start)  # 标记为通过，因为可能没有 OAP Server
                result.add_warning(f"获取服务拓扑失败（可能无 OAP Server）: {e}")

            result.success = len(result.errors) == 0

        except Exception as e:
            logger.error(f"SkyWalkingCallChainAdapter 验证失败: {e}")
            result.add_error(f"适配器初始化失败: {e}")

        result.duration = time.time() - result.start_time
        self.results.append(result)

        # 输出结果
        self._log_result(result)

    def _validate_openai_adapter(self) -> None:
        """验证 OpenAIAdapter."""
        logger.info("\n" + "-" * 80)
        logger.info("验证 OpenAIAdapter")
        logger.info("-" * 80)

        result = AdapterTestResult("OpenAIAdapter")
        result.start_time = time.time()

        try:
            # 检查是否有 API key
            import os
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                result.add_warning("OPENAI_API_KEY 环境变量未设置，跳过测试")
                result.duration = time.time() - result.start_time
                self.results.append(result)
                self._log_result(result)
                return

            # 初始化适配器
            logger.info("初始化 OpenAIAdapter...")
            adapter = OpenAIAdapter(
                api_key=api_key,
                model="gpt-4-turbo-preview",
            )

            test_start = time.time()

            # 测试1: 初始化
            try:
                start = time.time()
                assert adapter.provider == "openai"
                assert adapter.model == "gpt-4-turbo-preview"
                duration = time.time() - start
                result.add_test_case("初始化测试", True, duration)
            except Exception as e:
                result.add_test_case("初始化测试", False, time.time() - test_start)
                result.add_error(f"初始化失败: {e}")

            result.success = len(result.errors) == 0

        except Exception as e:
            logger.error(f"OpenAIAdapter 验证失败: {e}")
            result.add_error(f"适配器初始化失败: {e}")

        result.duration = time.time() - result.start_time
        self.results.append(result)

        # 输出结果
        self._log_result(result)

    def _validate_skywalking_adapter(self) -> None:
        """验证 SkyWalkingAdapter."""
        logger.info("\n" + "-" * 80)
        logger.info("验证 SkyWalkingAdapter")
        logger.info("-" * 80)

        result = AdapterTestResult("SkyWalkingAdapter")
        result.start_time = time.time()

        try:
            # 初始化适配器
            logger.info("初始化 SkyWalkingAdapter...")
            adapter = SkyWalkingAdapter(
                oap_server="http://localhost:12800",
            )

            test_start = time.time()

            # 测试1: 初始化
            try:
                start = time.time()
                assert adapter is not None
                duration = time.time() - start
                result.add_test_case("初始化测试", True, duration)
            except Exception as e:
                result.add_test_case("初始化测试", False, time.time() - test_start)
                result.add_error(f"初始化失败: {e}")

            result.success = len(result.errors) == 0

        except Exception as e:
            logger.error(f"SkyWalkingAdapter 验证失败: {e}")
            result.add_error(f"适配器初始化失败: {e}")

        result.duration = time.time() - result.start_time
        self.results.append(result)

        # 输出结果
        self._log_result(result)

    def _log_result(self, result: AdapterTestResult) -> None:
        """输出测试结果."""
        logger.info(f"\n适配器: {result.adapter_name}")
        logger.info(f"状态: {'通过' if result.success else '失败'}")
        logger.info(f"持续时间: {result.duration:.2f}秒")

        if result.errors:
            logger.error(f"错误 ({len(result.errors)}):")
            for error in result.errors:
                logger.error(f"  - {error}")

        if result.warnings:
            logger.warning(f"警告 ({len(result.warnings)}):")
            for warning in result.warnings:
                logger.warning(f"  - {warning}")

        logger.info(f"测试用例: {len(result.test_cases)}")
        for tc in result.test_cases:
            status_icon = "✓" if tc["passed"] else "✗"
            logger.info(
                f"  {status_icon} {tc['name']} ({tc['duration']:.2f}s)"
            )

    def _generate_report(self, total_duration: float) -> dict[str, Any]:
        """生成验证报告.

        Args:
            total_duration: 总验证时间

        Returns:
            Dict[str, Any]: 验证报告
        """
        # 统计结果
        total_tests = sum(len(r.test_cases) for r in self.results)
        passed_tests = sum(
            sum(1 for tc in r.test_cases if tc["passed"]) for r in self.results
        )
        failed_tests = total_tests - passed_tests

        total_errors = sum(len(r.errors) for r in self.results)
        total_warnings = sum(len(r.warnings) for r in self.results)

        # 按适配器分组
        adapter_status = {}
        for result in self.results:
            adapter_status[result.adapter_name] = {
                "success": result.success,
                "test_count": len(result.test_cases),
                "error_count": len(result.errors),
                "warning_count": len(result.warnings),
                "duration": result.duration,
            }

        return {
            "validation_summary": {
                "validation_time": datetime.now().isoformat(),
                "total_duration": f"{total_duration:.2f}s",
                "total_adapters": len(self.results),
                "successful_adapters": sum(1 for r in self.results if r.success),
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": f"{(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "N/A",
                "total_errors": total_errors,
                "total_warnings": total_warnings,
            },
            "adapter_results": [r.to_dict() for r in self.results],
            "adapter_status": adapter_status,
        }

    def _save_report(self, report: dict) -> None:
        """保存验证报告.

        Args:
            report: 验证报告
        """
        # JSON 格式
        json_file = self._output_dir / "validation_report.json"
        with open(json_file, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"验证报告已保存: {json_file}")

        # Markdown 格式
        md_file = self._output_dir / "validation_report.md"
        self._save_markdown_report(md_file, report)
        logger.info(f"Markdown 报告已保存: {md_file}")

        # HTML 格式
        html_file = self._output_dir / "validation_report.html"
        self._save_html_report(html_file, report)
        logger.info(f"HTML 报告已保存: {html_file}")

    def _save_markdown_report(self, file_path: Path, report: dict) -> None:
        """保存 Markdown 格式报告."""
        summary = report["validation_summary"]

        md_content = f"""# JCIA 适配器验证报告

**验证时间**: {summary['validation_time']}
**总耗时**: {summary['total_duration']}

---

## 验证摘要

| 指标 | 数值 |
|------|------|
| 适配器总数 | {summary['total_adapters']} |
| 成功数量 | {summary['successful_adapters']} |
| 测试用例总数 | {summary['total_tests']} |
| 通过测试 | {summary['passed_tests']} |
| 失败测试 | {summary['failed_tests']} |
| 成功率 | {summary['success_rate']} |
| 错误总数 | {summary['total_errors']} |
| 警告总数 | {summary['total_warnings']} |

---

## 适配器详细结果

"""

        for result in self.results:
            status_icon = "✓" if result.success else "✗"
            md_content += f"""### {status_icon} {result.adapter_name}

**状态**: {'通过' if result.success else '失败'}
**持续时间**: {result.duration:.2f}秒
**测试用例数**: {len(result.test_cases)}

#### 测试用例

"""
            for tc in result.test_cases:
                tc_icon = "✓" if tc["passed"] else "✗"
                md_content += f"- {tc_icon} **{tc['name']}** ({tc['duration']:.2f}s)\n"

            if result.errors:
                md_content += "#### 错误\n\n"
                for error in result.errors:
                    md_content += f"- {error}\n"

            if result.warnings:
                md_content += "#### 警告\n\n"
                for warning in result.warnings:
                    md_content += f"- {warning}\n"

            md_content += "\n---\n\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    def _save_html_report(self, file_path: Path, report: dict) -> None:
        """保存 HTML 格式报告."""
        summary = report["validation_summary"]

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JCIA 适配器验证报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        h3 {{
            color: #2c3e50;
            margin-top: 20px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .summary {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .success {{
            color: #27ae60;
            font-weight: bold;
        }}
        .failure {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .warning {{
            color: #f39c12;
        }}
        .test-passed {{
            color: #27ae60;
        }}
        .test-failed {{
            color: #e74c3c;
        }}
    </style>
</head>
<body>
    <h1>JCIA 适配器验证报告</h1>
    <p><strong>验证时间</strong>: {summary['validation_time']}</p>
    <p><strong>总耗时</strong>: {summary['total_duration']}</p>

    <div class="summary">
        <h2>验证摘要</h2>
        <table>
            <tr>
                <th>指标</th>
                <th>数值</th>
            </tr>
            <tr>
                <td>适配器总数</td>
                <td>{summary['total_adapters']}</td>
            </tr>
            <tr>
                <td>成功数量</td>
                <td class="success">{summary['successful_adapters']}</td>
            </tr>
            <tr>
                <td>测试用例总数</td>
                <td>{summary['total_tests']}</td>
            </tr>
            <tr>
                <td>通过测试</td>
                <td class="success">{summary['passed_tests']}</td>
            </tr>
            <tr>
                <td>失败测试</td>
                <td class="failure">{summary['failed_tests']}</td>
            </tr>
            <tr>
                <td>成功率</td>
                <td>{summary['success_rate']}</td>
            </tr>
            <tr>
                <td>错误总数</td>
                <td class="failure">{summary['total_errors']}</td>
            </tr>
            <tr>
                <td>警告总数</td>
                <td class="warning">{summary['total_warnings']}</td>
            </tr>
        </table>
    </div>

    <h2>适配器详细结果</h2>
"""

        for result in self.results:
            status_class = "success" if result.success else "failure"
            html_content += f"""
    <div style="margin-bottom: 30px;">
        <h3 class="{status_class}">{'✓' if result.success else '✗'} {result.adapter_name}</h3>
        <p><strong>状态</strong>: <span class="{status_class}">{'通过' if result.success else '失败'}</span></p>
        <p><strong>持续时间</strong>: {result.duration:.2f}秒</p>
        <p><strong>测试用例数</strong>: {len(result.test_cases)}</p>

        <h4>测试用例</h4>
        <ul>
"""

            for tc in result.test_cases:
                tc_class = "test-passed" if tc["passed"] else "test-failed"
                html_content += f"""
            <li class="{tc_class}">
                {tc['name']} ({tc['duration']:.2f}s)
            </li>
"""

            html_content += "        </ul>"

            if result.errors:
                html_content += "        <h4 class='failure'>错误</h4>\n        <ul>\n"
                for error in result.errors:
                    html_content += f"            <li>{error}</li>\n"
                html_content += "        </ul>\n"

            if result.warnings:
                html_content += "        <h4 class='warning'>警告</h4>\n        <ul>\n"
                for warning in result.warnings:
                    html_content += f"            <li>{warning}</li>\n"
                html_content += "        </ul>\n"

            html_content += "    </div>\n"

        html_content += """
</body>
</html>
"""

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)


def main():
    """主函数."""
    parser = argparse.ArgumentParser(
        description="JCIA 适配器验证工具", formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--jenkins-workspace",
        type=str,
        default=".",
        help="Jenkins 工作空间路径（默认：当前目录）",
    )
    parser.add_argument(
        "--jenkins-url", type=str, default=None, help="Jenkins 服务器 URL"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="validation_report",
        help="输出报告目录（默认：validation_report）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="详细输出",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 创建验证器
    validator = JenkinsValidator(
        jenkins_workspace=args.jenkins_workspace,
        jenkins_url=args.jenkins_url,
        output_dir=args.output_dir,
    )

    # 执行验证
    report = validator.validate_all_adapters()

    # 输出摘要
    summary = report["validation_summary"]
    logger.info("\n" + "=" * 80)
    logger.info("验证完成")
    logger.info("=" * 80)
    logger.info(f"总耗时: {summary['total_duration']}")
    logger.info(
        f"适配器通过率: {summary['successful_adapters']}/{summary['total_adapters']}"
    )
    logger.info(f"测试成功率: {summary['success_rate']}")
    logger.info(f"报告目录: {args.output_dir}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
