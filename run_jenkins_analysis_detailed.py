"""生成详细的 Jenkins 影响分析报告（包含代码对比和调用链）."""
from pathlib import Path
from typing import Any

from pydriller import Repository

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.adapters.tools.mock_call_chain_analyzer import MockCallChainAnalyzer
from jcia.core.use_cases.analyze_impact import AnalyzeImpactRequest, AnalyzeImpactUseCase
from jcia.core.services.impact_analysis_service import ImpactAnalysisService
from jcia.reports.base import ReportData


class EnhancedHTMLReporter:
    """增强版 HTML 报告生成器，包含代码对比和调用链."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def generate(self, data: ReportData):
        """生成报告."""
        self._ensure_output_dir()
        
        html = self._render_html(data)
        
        filename = self._get_output_filename("html")
        output_path = self.output_dir / filename
        output_path.write_text(html, encoding="utf-8")
        
        return type('ReportResult', (), {'success': True, 'output_path': output_path, 'content': html, 'size_bytes': len(html.encode("utf-8"))})

    def _ensure_output_dir(self):
        """确保输出目录存在."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_output_filename(self, format: str):
        """获取输出文件名."""
        from datetime import datetime
        return f"detailed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"

    def _render_html(self, data: ReportData) -> str:
        """渲染 HTML."""
        report_dict = data.to_dict()
        change_set = report_dict.get("change_set", {})
        impact_graph = report_dict.get("impact_graph", {})
        metadata = report_dict.get("metadata", {})
        
        html = self._get_header()
        
        # 提交信息
        html += self._render_commit_info(metadata)
        
        # 变更概览
        html += self._render_change_overview(change_set)
        
        # 代码变更详情及影响分析
        html += self._render_code_changes(change_set, metadata.get("diff_results", []), impact_graph)
        
        # 影响分析详情
        html += self._render_impact_analysis(impact_graph, change_set)
        
        # 调用链详情
        html += self._render_call_chain(impact_graph)
        
        html += self._get_footer()
        return html

    def _get_header(self):
        """获取 HTML 头部."""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jenkins 代码变更影响分析报告（详细版）</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .card h3 {
            color: #764ba2;
            margin: 20px 0 10px 0;
            border-left: 4px solid #764ba2;
            padding-left: 10px;
        }
        .diff-container {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            overflow-x: auto;
            margin: 15px 0;
        }
        .diff-view {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .diff-header {
            grid-column: 1 / -1;
            background: #e9ecef;
            padding: 10px;
            border-radius: 5px 5px 0 0;
            font-weight: bold;
        }
        .diff-left, .diff-right {
            padding: 15px;
        }
        .diff-left { border-right: 2px solid #dee2e6; }
        .diff-add { background: #e6ffed; }
        .diff-remove { background: #ffe6e6; }
        .diff-line-number {
            color: #999;
            width: 50px;
            display: inline-block;
            text-align: right;
            padding-right: 10px;
            border-right: 1px solid #dee2e6;
            margin-right: 10px;
        }
        .impact-node {
            background: #f8f9fa;
            border: 2px solid #667eea;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
        }
        .impact-node.high { border-color: #dc3545; }
        .impact-node.medium { border-color: #ffc107; }
        .impact-node.low { border-color: #28a745; }
        .impact-method {
            font-family: 'Courier New', monospace;
            font-size: 14px;
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 5px;
        }
        .call-chain {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
        }
        .call-chain-item {
            padding: 10px;
            margin: 5px 0;
            border-left: 3px solid #667eea;
            padding-left: 15px;
        }
        .call-chain-item.depth-1 { border-left-color: #667eea; }
        .call-chain-item.depth-2 { border-left-color: #764ba2; }
        .call-chain-item.depth-3 { border-left-color: #f093fb; }
        .call-chain-item.depth-4 { border-left-color: #4facfe; }
        .call-chain-item.depth-5 { border-left-color: #00f2fe; }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            margin: 0 5px;
        }
        .badge.direct { background: #667eea; color: white; }
        .badge.indirect { background: #764ba2; color: white; }
        .badge.high { background: #dc3545; color: white; }
        .badge.medium { background: #ffc107; color: #333; }
        .badge.low { background: #28a745; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Jenkins 代码变更影响分析报告（详细版）</h1>
            <p>包含代码对比、调用链分析和多层级影响传播</p>
        </div>
"""

    def _get_footer(self):
        """获取 HTML 尾部."""
        return """
        <div class="card">
            <p style="text-align: center; color: #666;">
                由 JCIA (Java Code Impact Analyzer) 生成<br>
                报告包含代码变更详情、影响分析和调用链推导过程
            </p>
        </div>
    </div>
</body>
</html>
"""

    def _render_commit_info(self, metadata):
        """渲染提交信息."""
        commit_details = metadata.get("commit_details", [])
        
        html = '<div class="card"><h2>📝 提交信息</h2>'
        
        if not commit_details:
            html += '<p>未获取到提交详情</p>'
        else:
            for commit in commit_details:
                html += f'<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #667eea;">'
                html += f'<h3 style="margin-top: 0;"><span class="badge" style="background: #667eea; color: white;">{commit["short_hash"]}</span> {commit["msg"]}</h3>'
                html += f'<p style="margin: 5px 0;"><strong>👤 作者:</strong> {commit["author"]}</p>'
                html += f'<p style="margin: 5px 0;"><strong>📅 时间:</strong> {commit["date"]}</p>'
                html += f'<p style="margin: 5px 0;"><strong>📄 变更文件 ({len(commit["files"])}):</strong></p>'
                html += '<div style="margin-left: 20px;">'
                for file in commit["files"]:
                    html += f'<code style="display: block; margin: 2px 0; padding: 4px; background: white; border-radius: 4px;">📁 {file}</code>'
                html += '</div></div>'
        
        html += '</div>'
        return html

    def _render_change_overview(self, change_set):
        """渲染变更概览."""
        return f"""
        <div class="card">
            <h2>📊 变更概览</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #1976d2;">{change_set.get('commit_count', 0)}</div>
                    <div>变更提交数</div>
                </div>
                <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #388e3c;">{len(change_set.get('file_changes', []))}</div>
                    <div>变更文件数</div>
                </div>
                <div style="background: #fff3e0; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #f57c00;">{len(change_set.get('changed_java_files', []))}</div>
                    <div>Java文件数</div>
                </div>
                <div style="background: #f3e5f5; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #7b1fa2;">{len(change_set.get('changed_methods', []))}</div>
                    <div>变更方法数</div>
                </div>
                <div style="background: #fce4ec; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #c2185b;">{change_set.get('total_insertions', 0)}</div>
                    <div>新增行数</div>
                </div>
                <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #388e3c;">{change_set.get('total_deletions', 0)}</div>
                    <div>删除行数</div>
                </div>
            </div>
        </div>
"""

    def _render_code_changes(self, change_set, diff_results, impact_graph):
        """渲染代码变更详情，按 commit 和文件分组."""
        html = '<div class="card"><h2>📝 代码变更详情及影响分析</h2>'
        
        # 获取节点列表以便查找影响
        nodes = impact_graph.get("nodes", [])
        
        # 构建文件到影响的映射
        file_impacts = {}
        for node in nodes:
            method_name = node.get("method_name", "")
            # 提取文件名
            if "::" in method_name:
                parts = method_name.split("::")
                if len(parts) >= 2:
                    class_part = parts[0].split(".")[-1]
                    file_impacts[method_name] = {
                        "file": f"{class_part}.java",
                        "severity": node.get("severity", "medium"),
                        "impact_type": node.get("impact_type", "direct"),
                        "upstream": node.get("upstream", []),
                        "downstream": node.get("downstream", []),
                    }
        
        for file_change in change_set.get("file_changes", []):
            if file_change["file_path"].endswith(".java"):
                file_name = file_change["file_path"].split("/")[-1]
                
                html += f'<div style="margin: 20px 0; border: 2px solid #667eea; border-radius: 10px; overflow: hidden;">'
                html += f'<div style="background: #667eea; color: white; padding: 15px;">'
                html += f'<h3 style="margin: 0;">📄 {file_name}</h3>'
                html += f'<p style="margin: 5px 0 0 0;">'
                html += f'<span class="badge" style="background: white; color: #667eea;">{file_change["change_type"]}</span>'
                html += f' +{file_change.get("insertions", 0)} / -{file_change.get("deletions", 0)}'
                html += '</p></div>'
                
                # 查找对应的差异
                diff_text = None
                for diff in diff_results:
                    if diff["file"] == file_change["file_path"]:
                        diff_text = diff["diff"]
                        break
                
                if diff_text:
                    html += f'<div style="padding: 15px;">'
                    html += self._render_diff_view(diff_text)
                    html += '</div>'
                
                # 显示方法变更及影响
                method_changes = file_change.get("method_changes", [])
                if method_changes:
                    html += f'<div style="padding: 15px; background: #f8f9fa;">'
                    html += '<h4 style="margin-top: 0;">🔧 变更的方法及影响</h4>'
                    
                    for method in method_changes:
                        method_name = method.get("full_name", method.get("method_name", "Unknown"))
                        
                        # 查找影响
                        impact = None
                        for mn, imp in file_impacts.items():
                            if method_name in mn or mn in method_name:
                                impact = imp
                                break
                        
                        html += f'<div style="margin: 15px 0; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #667eea;">'
                        html += f'<h5 style="margin-top: 0; color: #667eea;">{method_name}</h5>'
                        html += f'<p><span class="badge direct">{method.get("change_type", "modify")}</span>'
                        html += f' 行 {method.get("line_start", 0)}-{method.get("line_end", 0)}</p>'
                        
                        # 显示影响
                        if impact:
                            html += '<div style="margin-top: 10px;">'
                            html += f'<p><span class="badge {impact["severity"]}">{impact["severity"]}</span>'
                            html += f' 影响类型: {impact["impact_type"]}</p>'
                            
                            # 上游影响（被调用）
                            if impact["upstream"]:
                                html += '<p><strong>📤 被以下函数调用（需要回归测试）:</strong></p>'
                                html += '<div style="margin-left: 15px; background: #fff3e0; padding: 10px; border-radius: 5px;">'
                                for caller in impact["upstream"]:
                                    html += f'<code style="display: block; margin: 3px 0;">→ {caller}</code>'
                                html += '</div>'
                            
                            # 下游影响（调用）
                            if impact["downstream"]:
                                html += '<p style="margin-top: 10px;"><strong>📥 调用了以下函数:</strong></p>'
                                html += '<div style="margin-left: 15px; background: #e3f2fd; padding: 10px; border-radius: 5px;">'
                                for callee in impact["downstream"]:
                                    html += f'<code style="display: block; margin: 3px 0;">← {callee}</code>'
                                html += '</div>'
                            
                            html += '</div>'
                        else:
                            html += '<p style="color: #666; font-style: italic;">未检测到影响传播</p>'
                        
                        html += '</div>'
                    
                    html += '</div>'
                
                html += '</div>'
        
        html += '</div>'
        return html

    def _render_diff_view(self, diff_text):
        """渲染差异视图."""
        lines = diff_text.split('\n')
        left_lines = []
        right_lines = []
        current_left = 1
        current_right = 1
        
        for line in lines:
            if line.startswith('@@'):
                # 差异头部
                html = f'<div class="diff-header">{line}</div>'
                html += '<div class="diff-view">'
                if left_lines:
                    html += '<div class="diff-left">' + '\n'.join(left_lines) + '</div>'
                if right_lines:
                    html += '<div class="diff-right">' + '\n'.join(right_lines) + '</div>'
                html += '</div>'
                left_lines = []
                right_lines = []
            elif line.startswith('---'):
                continue
            elif line.startswith('+++'):
                continue
            elif line.startswith('-'):
                right_lines.append(f'<span class="diff-line-number">{current_right}</span> <span class="diff-remove">{line[1:]}</span>')
                current_right += 1
            elif line.startswith('+'):
                left_lines.append(f'<span class="diff-line-number">{current_left}</span> <span class="diff-add">{line[1:]}</span>')
                current_left += 1
            else:
                left_lines.append(f'<span class="diff-line-number">{current_left}</span> {line}')
                right_lines.append(f'<span class="diff-line-number">{current_right}</span> {line}')
                current_left += 1
                current_right += 1
        
        # 添加剩余的行
        if left_lines or right_lines:
            html += '<div class="diff-view">'
            if left_lines:
                html += '<div class="diff-left">' + '\n'.join(left_lines) + '</div>'
            if right_lines:
                html += '<div class="diff-right">' + '\n'.join(right_lines) + '</div>'
            html += '</div>'
        
        return html

    def _render_impact_analysis(self, impact_graph, change_set):
        """渲染影响分析详情."""
        html = '<div class="card"><h2>🎯 影响分析详情</h2>'
        
        nodes = impact_graph.get("nodes", [])
        edges = impact_graph.get("edges", [])
        
        # 将节点列表转换为字典方便查找
        nodes_dict = {node["method_name"]: node for node in nodes}
        
        if not nodes:
            html += '<p>未检测到影响传播</p>'
        else:
            html += f'<p>共分析 {len(nodes)} 个受影响的方法，{len(edges)} 个调用关系</p>'
            
            # 按严重程度分组
            high_severity = []
            medium_severity = []
            low_severity = []
            
            for node in nodes:
                if node.get("severity") == "high":
                    high_severity.append((node["method_name"], node))
                elif node.get("severity") == "medium":
                    medium_severity.append((node["method_name"], node))
                else:
                    low_severity.append((node["method_name"], node))
            
            # 显示高风险影响
            if high_severity:
                html += '<h3>🔴 高风险影响 (需要优先回归测试)</h3>'
                for method_name, node in high_severity:
                    html += self._render_impact_node(method_name, node, edges)
            
            # 显示中等风险影响
            if medium_severity:
                html += '<h3>🟡 中等风险影响</h3>'
                for method_name, node in medium_severity:
                    html += self._render_impact_node(method_name, node, edges)
            
            # 显示低风险影响
            if low_severity:
                html += '<h3>🟢 低风险影响</h3>'
                for method_name, node in low_severity:
                    html += self._render_impact_node(method_name, node, edges)
        
        html += '</div>'
        return html

    def _render_impact_node(self, method_name, node, edges):
        """渲染影响节点详情."""
        html = f'<div class="impact-node {node.get("severity", "medium")}">'
        html += f'<h4>{method_name}</h4>'
        html += f'<p><span class="badge direct">{node.get("impact_type", "direct")}</span>'
        html += f'<span class="badge {node.get("severity", "medium")}">{node.get("severity", "medium")}</span>'
        html += f'深度: {node.get("depth", 0)}</p>'
        
        # 查找上游和下游
        upstream = node.get("upstream", [])
        downstream = node.get("downstream", [])
        
        if upstream:
            html += '<p><strong>📤 被以下函数调用（上游）:</strong></p>'
            for caller in upstream:
                html += f'<code>{caller}</code> → '
        
        if downstream:
            html += '<p><strong>📥 调用了以下函数（下游）:</strong></p>'
            for callee in downstream:
                html += f'→ <code>{callee}</code><br>'
        
        html += '</div>'
        return html

    def _render_call_chain(self, impact_graph):
        """渲染调用链详情."""
        html = '<div class="card"><h2>🔗 调用链分析</h2>'
        
        nodes = impact_graph.get("nodes", [])
        root_methods = impact_graph.get("root_methods", [])
        
        # 将节点列表转换为字典
        nodes_dict = {node["method_name"]: node for node in nodes}
        
        if not root_methods:
            html += '<p>未检测到调用链</p>'
        else:
            html += '<p>以下是从变更方法开始的完整调用链：</p>'
            
            for root_method in root_methods:
                html += f'<div class="call-chain">'
                html += f'<h3>📍 从 <code>{root_method}</code> 开始的调用链</h3>'
                html += self._render_call_chain_recursive(root_method, nodes_dict, 1)
                html += '</div>'
        
        html += '</div>'
        return html

    def _render_call_chain_recursive(self, method_name, nodes, depth, visited=None):
        """递归渲染调用链."""
        if visited is None:
            visited = set()
        
        if method_name in visited or depth > 5:
            return ''
        
        visited.add(method_name)
        
        node = nodes.get(method_name)
        if not node:
            return ''
        
        html = f'<div class="call-chain-item depth-{depth}">'
        html += f'<strong>Depth {depth}:</strong> <code>{method_name}</code><br>'
        html += f'类型: {node.get("impact_type", "direct")} | 严重程度: {node.get("severity", "medium")}'
        
        # 递归显示下游
        downstream = node.get("downstream", [])
        if downstream:
            for callee in downstream:
                html += self._render_call_chain_recursive(callee, nodes, depth + 1, visited)
        
        html += '</div>'
        return html


# 主程序
# 配置
repo_path = str(Path(r"E:\Study\LLM\Java代码变更影响分析\jenkins-full"))
from_commit = "68f5885"  # Fix "Zeno's paradox"
to_commit = "52fa585"    # Replace dependency on jenkins.io

print("=" * 60)
print("生成详细的 Jenkins 代码变更影响分析报告")
print("=" * 60)

# 创建分析器
analyzer = PyDrillerAdapter(repo_path=repo_path)
call_chain_analyzer = MockCallChainAnalyzer(repo_path=repo_path)
use_case = AnalyzeImpactUseCase(
    change_analyzer=analyzer,
    call_chain_analyzer=call_chain_analyzer,
)

# 创建请求
request = AnalyzeImpactRequest(
    repo_path=Path(repo_path),
    from_commit=from_commit,
    to_commit=to_commit,
    max_depth=5,
    include_test_files=True,
)

# 执行分析
print("\n执行分析...")
response = use_case.execute(request)
print("✓ 分析完成")

# 获取每个 commit 的详细信息
print("\n获取提交详情...")
commit_details = []
for commit in Repository(repo_path, single=from_commit).traverse_commits():
    commit_details.append({
        "hash": commit.hash,
        "short_hash": commit.hash[:7],
        "msg": commit.msg,
        "author": commit.author.name,
        "date": commit.author_date.strftime("%Y-%m-%d %H:%M:%S"),
        "files": [f.filename for f in commit.modified_files],
    })
    break  # 只获取起始提交

for commit in Repository(repo_path, single=to_commit).traverse_commits():
    commit_details.append({
        "hash": commit.hash,
        "short_hash": commit.hash[:7],
        "msg": commit.msg,
        "author": commit.author.name,
        "date": commit.author_date.strftime("%Y-%m-%d %H:%M:%S"),
        "files": [f.filename for f in commit.modified_files],
    })
    break  # 只获取结束提交

print(f"✓ 收集到 {len(commit_details)} 个提交详情")

# 获取代码差异
print("\n获取代码差异...")
diff_results = []
for file_change in response.change_set.file_changes:
    if file_change.is_java_file:
        # 使用 git diff 获取详细差异
        import subprocess
        result = subprocess.run(
            ["git", "diff", f"{from_commit}..{to_commit}", "--", file_change.file_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout:
            diff_results.append({
                "file": file_change.file_path,
                "diff": result.stdout,
                "change_type": file_change.change_type.value,
            })

# 生成详细报告
print("\n生成详细报告...")
reporter = EnhancedHTMLReporter(output_dir=Path(r"E:\Study\LLM\Java代码变更影响分析\report"))

data = ReportData(
    title="Jenkins 代码变更影响分析报告（详细版）",
    test_run=None,
    impact_graph=response.impact_graph,
    change_set=response.change_set,
    comparison=None,
    metadata={
        "repo_path": str(repo_path),
        "from_commit": from_commit,
        "to_commit": to_commit,
        "max_depth": request.max_depth,
        "diff_results": diff_results,
        "commit_details": commit_details,
    },
)

result = reporter.generate(data)

if result.success:
    print(f"✓ 详细报告已生成")
    print(f"  路径: {result.output_path}")
    print(f"  大小: {result.size_bytes} 字节")
else:
    print(f"✗ 报告生成失败: {result.error_message}")

print("\n" + "=" * 60)
print("详细报告生成完成！")
print("=" * 60)
