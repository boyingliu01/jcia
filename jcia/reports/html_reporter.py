"""HTML报告生成器.

生成HTML格式的测试报告，包含可视化图表。
"""

from pathlib import Path
from typing import Any

from jcia.reports.base import BaseReporter, ReportData, ReportResult


class HTMLReporter(BaseReporter):
    """HTML报告生成器.

    生成HTML格式的测试报告，包含样式和可视化元素。
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        include_charts: bool = True,
        template_path: Path | None = None,
    ) -> None:
        """初始化HTML报告生成器.

        Args:
            output_dir: 输出目录
            include_charts: 是否包含图表
            template_path: 自定义模板路径
        """
        super().__init__(output_dir)
        self._include_charts = include_charts
        self._template_path = template_path

    def get_format(self) -> str:
        """获取报告格式.

        Returns:
            str: 报告格式标识
        """
        return "html"

    def generate(self, data: ReportData) -> ReportResult:
        """生成HTML报告.

        Args:
            data: 报告数据

        Returns:
            ReportResult: 报告生成结果
        """
        try:
            self._ensure_output_dir()

            # 生成HTML内容
            content = self._render_html(data)

            # 保存文件
            filename = self._get_output_filename("html")
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

    def _render_html(self, data: ReportData) -> str:
        """渲染HTML内容.

        Args:
            data: 报告数据

        Returns:
            str: HTML内容
        """
        report_dict = data.to_dict()

        # 提取测试运行数据
        test_run = report_dict.get("test_run", {})
        comparison = report_dict.get("comparison")
        impact_graph = report_dict.get("impact_graph")
        change_set = report_dict.get("change_set")

        html = self._get_html_header(data.title, report_dict.get("timestamp", ""))

        # 测试摘要
        if test_run:
            html += self._render_test_summary(test_run)

        # 测试对比
        if comparison:
            html += self._render_comparison(comparison)

        # 影响图
        if impact_graph:
            html += self._render_impact_graph(impact_graph)

        # 变更集
        if change_set:
            html += self._render_change_set(change_set)

        html += self._get_html_footer()

        return html

    def _get_html_header(self, title: str, timestamp: str) -> str:
        """获取HTML头部.

        Args:
            title: 报告标题
            timestamp: 时间戳

        Returns:
            str: HTML头部
        """
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --primary-color: #4CAF50;
            --danger-color: #f44336;
            --warning-color: #ff9800;
            --info-color: #2196F3;
            --bg-color: #f5f5f5;
            --card-bg: #ffffff;
            --text-color: #333333;
            --border-color: #e0e0e0;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--bg-color);
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, var(--primary-color), #45a049);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .header .timestamp {{
            opacity: 0.9;
            font-size: 0.9em;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            color: var(--primary-color);
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .stat-item {{
            background: var(--bg-color);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: var(--primary-color);
        }}
        .stat-value.passed {{ color: var(--primary-color); }}
        .stat-value.failed {{ color: var(--danger-color); }}
        .stat-value.skipped {{ color: var(--warning-color); }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .progress-bar {{
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--primary-color), #45a049);
            transition: width 0.3s ease;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        th {{
            background: var(--bg-color);
            font-weight: 600;
            color: var(--text-color);
        }}
        tr:hover {{
            background: var(--bg-color);
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        .badge.passed {{ background: #e8f5e9; color: var(--primary-color); }}
        .badge.failed {{ background: #ffebee; color: var(--danger-color); }}
        .badge.new {{ background: #e3f2fd; color: var(--info-color); }}
        .badge.removed {{ background: #fff3e0; color: var(--warning-color); }}
        .impact-list {{
            list-style: none;
        }}
        .impact-list li {{
            padding: 10px;
            margin: 5px 0;
            background: var(--bg-color);
            border-radius: 5px;
            border-left: 4px solid var(--primary-color);
        }}
        .impact-list li.high {{ border-left-color: var(--danger-color); }}
        .impact-list li.medium {{ border-left-color: var(--warning-color); }}
        .impact-list li.low {{ border-left-color: var(--info-color); }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p class="timestamp">生成时间: {timestamp}</p>
        </div>
"""

    def _get_html_footer(self) -> str:
        """获取HTML尾部.

        Returns:
            str: HTML尾部
        """
        return """
        <div class="footer">
            <p>由 JCIA (Java Code Impact Analyzer) 生成</p>
        </div>
    </div>
</body>
</html>
"""

    def _render_test_summary(self, test_run: dict[str, Any]) -> str:
        """渲染测试摘要.

        Args:
            test_run: 测试运行数据

        Returns:
            str: HTML内容
        """
        total = test_run.get("total_tests", 0)
        passed = test_run.get("passed_tests", 0)
        failed = test_run.get("failed_tests", 0)
        skipped = test_run.get("skipped_tests", 0)

        # 计算成功率
        success_rate_str = test_run.get("success_rate", "0.00%")
        if isinstance(success_rate_str, (int, float)):
            success_rate = success_rate_str * 100 if success_rate_str <= 1 else success_rate_str
        else:
            success_rate = float(success_rate_str.replace("%", "")) if success_rate_str else 0

        coverage = test_run.get("coverage", 0)
        if isinstance(coverage, dict):
            coverage = coverage.get("line_coverage", 0)

        return f"""
        <div class="card">
            <h2>测试摘要</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{total}</div>
                    <div class="stat-label">总测试数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value passed">{passed}</div>
                    <div class="stat-label">通过</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value failed">{failed}</div>
                    <div class="stat-label">失败</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value skipped">{skipped}</div>
                    <div class="stat-label">跳过</div>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <p><strong>成功率:</strong> {success_rate:.2f}%</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {success_rate}%"></div>
                </div>
            </div>
            <div style="margin-top: 15px;">
                <p><strong>行覆盖率:</strong> {coverage:.2f}%</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {coverage}%"></div>
                </div>
            </div>
        </div>
"""

    def _render_comparison(self, comparison: dict[str, Any]) -> str:
        """渲染测试对比.

        Args:
            comparison: 对比数据

        Returns:
            str: HTML内容
        """
        diff_summary = comparison.get("diff_summary", {})
        diffs = comparison.get("diffs", [])

        html = f"""
        <div class="card">
            <h2>测试对比</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{diff_summary.get("total_diffs", 0)}</div>
                    <div class="stat-label">总差异数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value passed">{diff_summary.get("new_passes", 0)}</div>
                    <div class="stat-label">新增通过</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value failed">{diff_summary.get("new_failures", 0)}</div>
                    <div class="stat-label">新增失败</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value failed">{diff_summary.get("regression_issues", 0)}</div>
                    <div class="stat-label">回归问题</div>
                </div>
            </div>
"""

        if diffs:
            html += """
            <table>
                <thead>
                    <tr>
                        <th>测试名称</th>
                        <th>基线状态</th>
                        <th>回归状态</th>
                        <th>差异类型</th>
                    </tr>
                </thead>
                <tbody>
"""
            for diff in diffs[:20]:  # 限制显示前20条
                baseline_status = diff.get("baseline_status", "-")
                regression_status = diff.get("regression_status", "-")
                diff_type = diff.get("diff_type", "UNKNOWN")

                baseline_class = "passed" if baseline_status == "passed" else "failed"
                regression_class = "passed" if regression_status == "passed" else "failed"

                html += f"""
                    <tr>
                        <td>{diff.get("full_name", "Unknown")}</td>
                        <td><span class="badge {baseline_class}">{baseline_status}</span></td>
                        <td><span class="badge {regression_class}">{regression_status}</span></td>
                        <td><span class="badge new">{diff_type}</span></td>
                    </tr>
"""

            html += """
                </tbody>
            </table>
"""

        html += "</div>"
        return html

    def _render_impact_graph(self, impact_graph: dict[str, Any]) -> str:
        """渲染影响图.

        Args:
            impact_graph: 影响图数据

        Returns:
            str: HTML内容
        """
        nodes = impact_graph.get("nodes", [])

        html = f"""
        <div class="card">
            <h2>影响分析</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{impact_graph.get("total_affected_methods", 0)}</div>
                    <div class="stat-label">受影响方法</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{impact_graph.get("direct_impact_count", 0)}</div>
                    <div class="stat-label">直接影响</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{impact_graph.get("indirect_impact_count", 0)}</div>
                    <div class="stat-label">间接影响</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value failed">{impact_graph.get("high_severity_count", 0)}</div>
                    <div class="stat-label">高风险</div>
                </div>
            </div>
"""

        if nodes:
            html += """
            <h3 style="margin-top: 20px;">受影响的方法</h3>
            <ul class="impact-list">
"""
            for node in nodes[:15]:  # 限制显示前15个
                severity = node.get("severity", "medium")
                html += f"""
                <li class="{severity}">
                    <strong>{node.get("method_name", "Unknown")}</strong>
                    <br><small>类: {node.get("class_name", "Unknown")} | 
                    影响类型: {node.get("impact_type", "unknown")} | 
                    深度: {node.get("depth", 0)}</small>
                </li>
"""
            html += "</ul>"

        html += "</div>"
        return html

    def _render_change_set(self, change_set: dict[str, Any]) -> str:
        """渲染变更集.

        Args:
            change_set: 变更集数据

        Returns:
            str: HTML内容
        """
        changed_files = change_set.get("changed_files", [])
        changed_methods = change_set.get("changed_methods", [])

        html = f"""
        <div class="card">
            <h2>代码变更</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{len(changed_files)}</div>
                    <div class="stat-label">变更文件</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{len(changed_methods)}</div>
                    <div class="stat-label">变更方法</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value passed">+{change_set.get("total_insertions", 0)}</div>
                    <div class="stat-label">新增行</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value failed">-{change_set.get("total_deletions", 0)}</div>
                    <div class="stat-label">删除行</div>
                </div>
            </div>
"""

        if changed_files:
            html += """
            <h3 style="margin-top: 20px;">变更文件列表</h3>
            <table>
                <thead>
                    <tr>
                        <th>文件路径</th>
                    </tr>
                </thead>
                <tbody>
"""
            for file_path in changed_files[:20]:
                html += f"<tr><td>{file_path}</td></tr>"

            html += """
                </tbody>
            </table>
"""

        html += "</div>"
        return html
