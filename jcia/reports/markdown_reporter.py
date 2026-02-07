"""Markdown报告生成器.

生成Markdown格式的测试报告，适合文档集成和代码审查。
"""

from pathlib import Path
from typing import Any

from jcia.reports.base import BaseReporter, ReportData, ReportResult


class MarkdownReporter(BaseReporter):
    """Markdown报告生成器.

    生成Markdown格式的测试报告，适合GitHub、GitLab等平台展示。
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        include_toc: bool = True,
    ) -> None:
        """初始化Markdown报告生成器.

        Args:
            output_dir: 输出目录
            include_toc: 是否包含目录
        """
        super().__init__(output_dir)
        self._include_toc = include_toc

    def get_format(self) -> str:
        """获取报告格式.

        Returns:
            str: 报告格式标识
        """
        return "markdown"

    def generate(self, data: ReportData) -> ReportResult:
        """生成Markdown报告.

        Args:
            data: 报告数据

        Returns:
            ReportResult: 报告生成结果
        """
        try:
            self._ensure_output_dir()

            # 生成Markdown内容
            content = self._render_markdown(data)

            # 保存文件
            filename = self._get_output_filename("md")
            output_path = self._output_dir / filename
            output_path.write_text(content, encoding="utf-8")

            return ReportResult(
                success=True,
                output_path=output_path,
                content=content,
                format=self.get_format(),
                size_bytes=len(content.encode("utf-8")),
            )

        except Exception as e:
            return ReportResult(
                success=False,
                format=self.get_format(),
                error_message=str(e),
            )

    def generate_to_string(self, data: ReportData) -> str:
        """生成Markdown字符串（不保存文件）.

        Args:
            data: 报告数据

        Returns:
            str: Markdown字符串
        """
        return self._render_markdown(data)

    def _render_markdown(self, data: ReportData) -> str:
        """渲染Markdown内容.

        Args:
            data: 报告数据

        Returns:
            str: Markdown内容
        """
        report_dict = data.to_dict()

        lines = []

        # 标题
        lines.append(f"# {data.title}")
        lines.append("")
        lines.append(f"> 生成时间: {report_dict.get('timestamp', '')}")
        lines.append("")

        # 目录
        if self._include_toc:
            lines.extend(self._generate_toc(report_dict))

        # 测试摘要
        test_run = report_dict.get("test_run")
        if test_run:
            lines.extend(self._render_test_summary(test_run))

        # 测试对比
        comparison = report_dict.get("comparison")
        if comparison:
            lines.extend(self._render_comparison(comparison))

        # 影响分析
        impact_graph = report_dict.get("impact_graph")
        if impact_graph:
            lines.extend(self._render_impact_graph(impact_graph))

        # 代码变更
        change_set = report_dict.get("change_set")
        if change_set:
            lines.extend(self._render_change_set(change_set))

        # 页脚
        lines.append("---")
        lines.append("")
        lines.append("*由 JCIA (Java Code Impact Analyzer) 生成*")

        return "\n".join(lines)

    def _generate_toc(self, report_dict: dict[str, Any]) -> list[str]:
        """生成目录.

        Args:
            report_dict: 报告数据字典

        Returns:
            list[str]: 目录行列表
        """
        lines = ["## 目录", ""]

        if report_dict.get("test_run"):
            lines.append("- [测试摘要](#测试摘要)")
        if report_dict.get("comparison"):
            lines.append("- [测试对比](#测试对比)")
        if report_dict.get("impact_graph"):
            lines.append("- [影响分析](#影响分析)")
        if report_dict.get("change_set"):
            lines.append("- [代码变更](#代码变更)")

        lines.append("")
        return lines

    def _render_test_summary(self, test_run: dict[str, Any]) -> list[str]:
        """渲染测试摘要.

        Args:
            test_run: 测试运行数据

        Returns:
            list[str]: Markdown行列表
        """
        lines = ["## 测试摘要", ""]

        total = test_run.get("total_tests", 0)
        passed = test_run.get("passed_tests", 0)
        failed = test_run.get("failed_tests", 0)
        skipped = test_run.get("skipped_tests", 0)
        success_rate = test_run.get("success_rate", "0.00%")

        # 统计表格
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 总测试数 | {total} |")
        lines.append(f"| ✅ 通过 | {passed} |")
        lines.append(f"| ❌ 失败 | {failed} |")
        lines.append(f"| ⏭️ 跳过 | {skipped} |")
        lines.append(f"| 成功率 | {success_rate} |")
        lines.append("")

        # 覆盖率信息
        coverage = test_run.get("coverage")
        if coverage:
            if isinstance(coverage, dict):
                lines.append("### 覆盖率")
                lines.append("")
                lines.append("| 类型 | 覆盖率 |")
                lines.append("|------|--------|")
                lines.append(f"| 行覆盖率 | {coverage.get('line_coverage', 0):.2f}% |")
                lines.append(f"| 分支覆盖率 | {coverage.get('branch_coverage', 0):.2f}% |")
                lines.append(f"| 方法覆盖率 | {coverage.get('method_coverage', 0):.2f}% |")
                lines.append(f"| 类覆盖率 | {coverage.get('class_coverage', 0):.2f}% |")
                lines.append("")
            else:
                lines.append(f"**行覆盖率**: {coverage:.2f}%")
                lines.append("")

        return lines

    def _render_comparison(self, comparison: dict[str, Any]) -> list[str]:
        """渲染测试对比.

        Args:
            comparison: 对比数据

        Returns:
            list[str]: Markdown行列表
        """
        lines = ["## 测试对比", ""]

        diff_summary = comparison.get("diff_summary", {})
        diffs = comparison.get("diffs", [])

        # 摘要
        lines.append("### 差异摘要")
        lines.append("")
        lines.append("| 类型 | 数量 |")
        lines.append("|------|------|")
        lines.append(f"| 总差异数 | {diff_summary.get('total_diffs', 0)} |")
        lines.append(f"| 🆕 新增通过 | {diff_summary.get('new_passes', 0)} |")
        lines.append(f"| 🔴 新增失败 | {diff_summary.get('new_failures', 0)} |")
        lines.append(f"| ⚠️ 回归问题 | {diff_summary.get('regression_issues', 0)} |")
        lines.append("")

        # 差异详情
        if diffs:
            lines.append("### 差异详情")
            lines.append("")
            lines.append("| 测试名称 | 基线状态 | 回归状态 | 差异类型 |")
            lines.append("|----------|----------|----------|----------|")
            for diff in diffs[:20]:
                full_name = diff.get("full_name", "Unknown")
                baseline = diff.get("baseline_status", "-")
                regression = diff.get("regression_status", "-")
                diff_type = diff.get("diff_type", "UNKNOWN")
                lines.append(f"| `{full_name}` | {baseline} | {regression} | {diff_type} |")
            lines.append("")

            if len(diffs) > 20:
                lines.append(f"*... 还有 {len(diffs) - 20} 条差异未显示*")
                lines.append("")

        return lines

    def _render_impact_graph(self, impact_graph: dict[str, Any]) -> list[str]:
        """渲染影响分析.

        Args:
            impact_graph: 影响图数据

        Returns:
            list[str]: Markdown行列表
        """
        lines = ["## 影响分析", ""]

        # 统计信息
        lines.append("### 影响统计")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 受影响方法总数 | {impact_graph.get('total_affected_methods', 0)} |")
        lines.append(f"| 直接影响 | {impact_graph.get('direct_impact_count', 0)} |")
        lines.append(f"| 间接影响 | {impact_graph.get('indirect_impact_count', 0)} |")
        lines.append(f"| 🔴 高风险 | {impact_graph.get('high_severity_count', 0)} |")
        lines.append("")

        # 受影响的类
        affected_classes = impact_graph.get("affected_classes", [])
        if affected_classes:
            lines.append("### 受影响的类")
            lines.append("")
            for cls in affected_classes[:10]:
                lines.append(f"- `{cls}`")
            lines.append("")

        # 受影响的方法
        nodes = impact_graph.get("nodes", [])
        if nodes:
            lines.append("### 受影响的方法")
            lines.append("")
            lines.append("| 方法名 | 类名 | 影响类型 | 严重程度 |")
            lines.append("|--------|------|----------|----------|")
            for node in nodes[:15]:
                method = node.get("method_name", "Unknown")
                class_name = node.get("class_name", "Unknown")
                impact_type = node.get("impact_type", "unknown")
                severity = node.get("severity", "medium")
                severity_emoji = (
                    "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢"
                )
                lines.append(
                    f"| `{method}` | `{class_name}` | {impact_type} | {severity_emoji} {severity} |"
                )
            lines.append("")

        return lines

    def _render_change_set(self, change_set: dict[str, Any]) -> list[str]:
        """渲染代码变更.

        Args:
            change_set: 变更集数据

        Returns:
            list[str]: Markdown行列表
        """
        lines = ["## 代码变更", ""]

        changed_files = change_set.get("changed_files", [])
        changed_methods = change_set.get("changed_methods", [])

        # 统计
        lines.append("### 变更统计")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 变更文件数 | {len(changed_files)} |")
        lines.append(f"| 变更方法数 | {len(changed_methods)} |")
        lines.append(f"| ➕ 新增行数 | {change_set.get('total_insertions', 0)} |")
        lines.append(f"| ➖ 删除行数 | {change_set.get('total_deletions', 0)} |")
        lines.append("")

        # 变更文件列表
        if changed_files:
            lines.append("### 变更文件")
            lines.append("")
            for file_path in changed_files[:20]:
                lines.append(f"- `{file_path}`")
            lines.append("")

            if len(changed_files) > 20:
                lines.append(f"*... 还有 {len(changed_files) - 20} 个文件未显示*")
                lines.append("")

        # 变更方法列表
        if changed_methods:
            lines.append("### 变更方法")
            lines.append("")
            for method in changed_methods[:15]:
                lines.append(f"- `{method}`")
            lines.append("")

            if len(changed_methods) > 15:
                lines.append(f"*... 还有 {len(changed_methods) - 15} 个方法未显示*")
                lines.append("")

        return lines
