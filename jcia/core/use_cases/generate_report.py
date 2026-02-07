"""生成测试报告用例.

负责生成多种格式的测试报告，包括JSON、HTML、Markdown和控制台输出。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jcia.core.entities.change_set import ChangeSet
    from jcia.core.entities.impact_graph import ImpactGraph
    from jcia.core.entities.test_run import TestRun


@dataclass
class GenerateReportRequest:
    """生成报告请求.

    Attributes:
        output_dir: 输出目录
        format: 报告格式（json/html/markdown/console）
        test_run: 测试运行结果
        impact_graph: 影响图（可选）
        change_set: 变更集合（可选）
        include_details: 是否包含详细信息
        include_charts: 是否包含图表
    """

    output_dir: Path
    format: str = "json"
    test_run: "TestRun | None" = None
    impact_graph: "ImpactGraph | None" = None
    change_set: "ChangeSet | None" = None
    include_details: bool = True
    include_charts: bool = False


@dataclass
class GenerateReportResponse:
    """生成报告响应.

    Attributes:
        report_path: 生成的报告文件路径
        format: 报告格式
        content: 报告内容（可选）
        metadata: 额外元数据
    """

    report_path: Path | None = None
    format: str = "json"
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class GenerateReportUseCase:
    """生成测试报告用例.

    生成多种格式的测试报告，包括JSON、HTML、Markdown和控制台输出。

    流程：
        1. 验证请求参数
        2. 准备报告数据
        3. 根据格式生成报告
        4. 保存报告文件（非console格式）
        5. 生成响应
    """

    def __init__(self) -> None:
        """初始化用例."""

    def execute(self, request: GenerateReportRequest) -> GenerateReportResponse:
        """执行生成报告用例.

        Args:
            request: 生成报告请求

        Returns:
            GenerateReportResponse: 生成响应

        Raises:
            ValueError: 请求参数无效
            Exception: 生成过程中发生错误
        """
        # 验证请求
        self._validate_request(request)

        # 准备报告数据
        report_data = self._prepare_report_data(request)

        # 根据格式生成报告
        if request.format == "json":
            response = self._generate_json_report(request, report_data)
        elif request.format == "html":
            response = self._generate_html_report(request, report_data)
        elif request.format == "markdown":
            response = self._generate_markdown_report(request, report_data)
        elif request.format == "console":
            response = self._generate_console_report(request, report_data)
        else:
            msg = f"不支持的报告格式: {request.format}"
            raise ValueError(msg)

        return response

    def _validate_request(self, request: GenerateReportRequest) -> None:
        """验证请求参数.

        Args:
            request: 生成报告请求

        Raises:
            ValueError: 请求参数无效
        """
        if not request.output_dir.exists():
            msg = f"输出目录不存在: {request.output_dir}"
            raise ValueError(msg)

        supported_formats = ["json", "html", "markdown", "console"]
        if request.format not in supported_formats:
            msg = f"不支持的格式: {request.format}，支持: {supported_formats}"
            raise ValueError(msg)

    def _prepare_report_data(self, request: GenerateReportRequest) -> dict[str, Any]:
        """准备报告数据.

        Args:
            request: 生成报告请求

        Returns:
            Dict[str, Any]: 报告数据
        """
        report_data = {
            "timestamp": self._get_timestamp(),
            "test_run": None,
            "impact_graph": None,
            "change_set": None,
        }

        if request.test_run:
            report_data["test_run"] = self._serialize_test_run(request.test_run)

        if request.impact_graph:
            report_data["impact_graph"] = request.impact_graph.to_dict()

        if request.change_set:
            report_data["change_set"] = request.change_set.to_dict()

        return report_data

    def _generate_json_report(
        self, request: GenerateReportRequest, report_data: dict[str, Any]
    ) -> GenerateReportResponse:
        """生成JSON格式报告.

        Args:
            request: 生成报告请求
            report_data: 报告数据

        Returns:
            GenerateReportResponse: 生成响应
        """
        import json

        content = json.dumps(report_data, indent=2, ensure_ascii=False)

        # 保存文件（使用时间戳作为文件名，去除冒号避免Windows文件名问题）
        timestamp_for_filename = self._get_timestamp().replace(":", "-").replace(".", "-")
        report_path = request.output_dir / f"test_report_{timestamp_for_filename}.json"
        report_path.write_text(content, encoding="utf-8")

        return GenerateReportResponse(
            report_path=report_path,
            format="json",
            content=content,
            metadata={"size_bytes": len(content)},
        )

    def _generate_html_report(
        self, request: GenerateReportRequest, report_data: dict[str, Any]
    ) -> GenerateReportResponse:
        """生成HTML格式报告.

        Args:
            request: 生成报告请求
            report_data: 报告数据

        Returns:
            GenerateReportResponse: 生成响应
        """
        # 简单的HTML模板
        html_content = self._create_html_template(report_data, request.include_details)

        # 保存文件（使用时间戳作为文件名，去除冒号避免Windows文件名问题）
        timestamp_for_filename = self._get_timestamp().replace(":", "-").replace(".", "-")
        report_path = request.output_dir / f"test_report_{timestamp_for_filename}.html"
        report_path.write_text(html_content, encoding="utf-8")

        return GenerateReportResponse(
            report_path=report_path,
            format="html",
            content=html_content,
            metadata={"size_bytes": len(html_content)},
        )

    def _generate_markdown_report(
        self, request: GenerateReportRequest, report_data: dict[str, Any]
    ) -> GenerateReportResponse:
        """生成Markdown格式报告.

        Args:
            request: 生成报告请求
            report_data: 报告数据

        Returns:
            GenerateReportResponse: 生成响应
        """
        md_content = self._create_markdown_content(report_data, request.include_details)

        # 保存文件（使用时间戳作为文件名，去除冒号避免Windows文件名问题）
        timestamp_for_filename = self._get_timestamp().replace(":", "-").replace(".", "-")
        report_path = request.output_dir / f"test_report_{timestamp_for_filename}.md"
        report_path.write_text(md_content, encoding="utf-8")

        return GenerateReportResponse(
            report_path=report_path,
            format="markdown",
            content=md_content,
            metadata={"size_bytes": len(md_content)},
        )

    def _generate_console_report(
        self, request: GenerateReportRequest, report_data: dict[str, Any]
    ) -> GenerateReportResponse:
        """生成控制台格式报告.

        Args:
            request: 生成报告请求
            report_data: 报告数据

        Returns:
            GenerateReportResponse: 生成响应
        """
        content = self._create_console_output(report_data, request.include_details)

        return GenerateReportResponse(
            report_path=None,
            format="console",
            content=content,
            metadata={"size_bytes": len(content)},
        )

    def _serialize_test_run(self, test_run: "TestRun") -> dict[str, Any]:
        """序列化测试运行对象.

        Args:
            test_run: 测试运行对象

        Returns:
            Dict[str, Any]: 序列化后的数据
        """
        return {
            "commit_hash": test_run.commit_hash,
            "run_type": test_run.run_type.value if test_run.run_type else None,
            "status": test_run.status.value if test_run.status else None,
            "total_tests": test_run.total_tests,
            "passed_tests": test_run.passed_tests,
            "failed_tests": test_run.failed_tests,
            "success_rate": test_run.success_rate,
            "coverage": (
                {
                    "line_coverage": test_run.coverage.line_coverage if test_run.coverage else 0.0,
                    "branch_coverage": test_run.coverage.branch_coverage
                    if test_run.coverage
                    else 0.0,
                    "method_coverage": test_run.coverage.method_coverage
                    if test_run.coverage
                    else 0.0,
                    "class_coverage": test_run.coverage.class_coverage
                    if test_run.coverage
                    else 0.0,
                }
                if test_run.coverage
                else None
            ),
        }

    def _create_html_template(self, report_data: dict[str, Any], include_details: bool) -> str:
        """创建HTML模板.

        Args:
            report_data: 报告数据
            include_details: 是否包含详细信息

        Returns:
            str: HTML内容
        """

        summary = report_data.get("test_run", {})
        test_run_data = summary if summary else {}

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {report_data.get("timestamp", "")}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .stat {{ display: inline-block; margin: 10px; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>测试报告</h1>
    <p>生成时间: {report_data.get("timestamp", "")}</p>

    <div class="summary">
        <h2>测试摘要</h2>
        <p>总测试数: {test_run_data.get("total_tests", 0)}</p>
        <p>通过测试数: <span class="passed">{test_run_data.get("passed_tests", 0)}</span></p>
        <p>失败测试数: <span class="failed">{test_run_data.get("failed_tests", 0)}</span></p>
        <p>成功率: {test_run_data.get("success_rate", 0):.2%}</p>
    </div>
"""

        if include_details and test_run_data.get("coverage"):
            html += "<h2>覆盖率</h2>"
            coverage = test_run_data["coverage"]
            if coverage:
                html += f"""
    <ul>
        <li>行覆盖率: {coverage.get("line_coverage", 0):.2%}</li>
        <li>分支覆盖率: {coverage.get("branch_coverage", 0):.2%}</li>
        <li>方法覆盖率: {coverage.get("method_coverage", 0):.2%}</li>
        <li>类覆盖率: {coverage.get("class_coverage", 0):.2%}</li>
    </ul>
"""

        html += """
</body>
</html>"""
        return html

    def _create_markdown_content(self, report_data: dict[str, Any], include_details: bool) -> str:
        """创建Markdown内容.

        Args:
            report_data: 报告数据
            include_details: 是否包含详细信息

        Returns:
            str: Markdown内容
        """
        summary = report_data.get("test_run", {})
        test_run_data = summary if summary else {}

        md = "# 测试报告\n\n"
        md += f"生成时间: {report_data.get('timestamp', '')}\n\n"

        md += "## 测试摘要\n\n"
        md += f"- 总测试数: {test_run_data.get('total_tests', 0)}\n"
        md += f"- 通过测试数: {test_run_data.get('passed_tests', 0)}\n"
        md += f"- 失败测试数: {test_run_data.get('failed_tests', 0)}\n"
        md += f"- 成功率: {test_run_data.get('success_rate', 0):.2%}\n\n"

        if include_details and test_run_data.get("coverage"):
            md += "## 覆盖率\n\n"
            coverage = test_run_data["coverage"]
            if coverage:
                md += f"- 行覆盖率: {coverage.get('line_coverage', 0):.2%}\n"
                md += f"- 分支覆盖率: {coverage.get('branch_coverage', 0):.2%}\n"
                md += f"- 方法覆盖率: {coverage.get('method_coverage', 0):.2%}\n"
                md += f"- 类覆盖率: {coverage.get('class_coverage', 0):.2%}\n\n"

        return md

    def _create_console_output(self, report_data: dict[str, Any], include_details: bool) -> str:
        """创建控制台输出.

        Args:
            report_data: 报告数据
            include_details: 是否包含详细信息

        Returns:
            str: 控制台输出内容
        """
        summary = report_data.get("test_run", {})
        test_run_data = summary if summary else {}

        output = "=" * 60 + "\n"
        output += "测试报告\n"
        output += "=" * 60 + "\n"
        output += f"生成时间: {report_data.get('timestamp', '')}\n\n"

        output += "-" * 40 + "\n"
        output += "测试摘要\n"
        output += "-" * 40 + "\n"
        output += f"总测试数: {test_run_data.get('total_tests', 0)}\n"
        output += f"通过测试数: {test_run_data.get('passed_tests', 0)}\n"
        output += f"失败测试数: {test_run_data.get('failed_tests', 0)}\n"
        output += f"成功率: {test_run_data.get('success_rate', 0):.2%}\n\n"

        if include_details and test_run_data.get("coverage"):
            output += "-" * 40 + "\n"
            output += "覆盖率\n"
            output += "-" * 40 + "\n"
            coverage = test_run_data["coverage"]
            if coverage:
                output += f"行覆盖率: {coverage.get('line_coverage', 0):.2%}\n"
                output += f"分支覆盖率: {coverage.get('branch_coverage', 0):.2%}\n"
                output += f"方法覆盖率: {coverage.get('method_coverage', 0):.2%}\n"
                output += f"类覆盖率: {coverage.get('class_coverage', 0):.2%}\n\n"

        output += "=" * 60 + "\n"

        return output

    def _get_timestamp(self) -> str:
        """获取当前时间戳.

        Returns:
            str: ISO格式时间戳
        """
        from datetime import datetime

        return datetime.now().isoformat()
