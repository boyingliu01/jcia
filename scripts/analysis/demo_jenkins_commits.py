#!/usr/bin/env python3
"""
JCIA Jenkins提交影响分析演示

对Jenkins代码仓库中的5个Java提交进行代码影响分析，展示JCIA的实际应用效果。
"""

import sys
import subprocess
from pathlib import Path

# 项目根目录
project_root = Path(__file__).parent.parent.parent

# Jenkins代码仓库路径
JENKINS_REPO_PATH = project_root / "jenkins"

# 5个要分析的Jenkins Java提交
JENKINS_COMMITS = [
    {
        "hash": "33b3b3b",
        "message": "Fix sidebar navigation for non-ASCII localized section headers (#26068)",
        "author": "AMOGH PARAMAR",
        "date": "2026-01-20",
        "description": "修复非ASCII本地化节头部的侧边栏导航问题"
    },
    {
        "hash": "c2fd9da8",
        "message": "Fix race condition during initial admin account creation (#26036)",
        "author": "Pankaj Kumar Singh",
        "date": "2026-01-04",
        "description": "修复初始管理员账户创建时的竞态条件"
    },
    {
        "hash": "11acb48bb",
        "message": "Fix PluginWrapper bug and cleanup Javadoc placeholders (#25984)",
        "author": "Shubham Chauhan",
        "date": "2025-12-30",
        "description": "修复PluginWrapper错误并清理Javadoc占位符"
    },
    {
        "hash": "2acba5d6",
        "message": "Add retry to flaky test in ResponseTimeMonitorTest (#10654)",
        "author": "Strangelookingnerd",
        "date": "2025-05-15",
        "description": "为ResponseTimeMonitorTest中不稳定的测试添加重试"
    },
    {
        "hash": "d6e2c7ca",
        "message": "Refine Add button for repeatable lists (#10913)",
        "author": "Jan Faracik",
        "date": "2025-08-07",
        "description": "优化可重复列表的添加按钮"
    },
]


def analyze_commit_with_jcia(commit_hash: str) -> dict:
    """使用JCIA CLI分析单个提交"""
    print(f"正在分析提交: {commit_hash}")

    try:
        # 使用JCIA CLI进行影响分析
        result = subprocess.run(
            [
                sys.executable, "-m", "jcia",
                "analyze",
                "--repo-path", str(JENKINS_REPO_PATH),
                "--from-commit", commit_hash,
                "--to-commit", commit_hash,
                "--max-depth", "10",
                "--output-format", "json"
            ],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(project_root)
        )

        if result.returncode == 0:
            import json
            try:
                data = json.loads(result.stdout)
                return {
                    "success": True,
                    "data": data,
                    "output": result.stdout
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Failed to parse JSON output",
                    "output": result.stdout
                }
        else:
            return {
                "success": False,
                "error": f"JCIA CLI failed with code {result.returncode}",
                "output": result.stderr
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Analysis timeout (300s)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def generate_markdown_report(analysis_results: list[dict]) -> str:
    """生成Markdown格式的分析报告"""
    lines = []
    lines.append("# JCIA Jenkins代码影响分析演示报告\n")
    lines.append(f"**生成时间**: 2026-02-22\n")
    lines.append(f"**分析工具**: JCIA (Java Code Impact Analyzer)\n")
    lines.append(f"**分析仓库**: Jenkins (git)\n")
    lines.append(f"**分析提交数**: {len(analysis_results)}\n")
    lines.append("---\n")

    total_java_files = 0
    total_affected_methods = 0
    successful_analyses = 0

    for i, (commit_info, analysis_result) in enumerate(analysis_results, 1):
        lines.append(f"## {i}. {commit_info['message'][:80]}\n")
        lines.append(f"**提交哈希**: `{commit_info['hash']}`\n")
        lines.append(f"**作者**: {commit_info['author']}\n")
        lines.append(f"**日期**: {commit_info['date']}\n")
        lines.append(f"**描述**: {commit_info['description']}\n")
        lines.append("---\n")

        # 分析结果
        if analysis_result.get("success"):
            successful_analyses += 1
            data = analysis_result.get("data", {})
            lines.append("### 分析状态\n")
            lines.append("✅ 分析成功\n\n")

            # 提取分析数据
            try:
                changed_files = data.get("changed_files", [])
                java_files = [f for f in changed_files if f.get("file_path", "").endswith(".java")]
                total_java_files += len(java_files)

                affected_methods = data.get("affected_methods", [])
                total_affected_methods += len(affected_methods)

                impact_graph = data.get("impact_graph", {})

                lines.append("### 变更统计\n")
                lines.append(f"- 变更文件数: {len(changed_files)}\n")
                lines.append(f"- Java文件数: {len(java_files)}\n")
                lines.append("\n")

                if java_files:
                    lines.append("变更的Java文件:\n")
                    for jf in java_files[:5]:
                        fp = jf.get("file_path", "Unknown")
                        change_type = jf.get("change_type", "Unknown")
                        lines.append(f"  - `{fp}` ({change_type})\n")
                    if len(java_files) > 5:
                        lines.append(f"  ... 还有 {len(java_files) - 5} 个文件\n")

                if affected_methods:
                    lines.append(f"### 影响分析结果\n")
                    lines.append(f"**受影响方法总数**: {len(affected_methods)}\n")
                    lines.append("\n#### 主要受影响方法 (前10个)\n")
                    for j, method in enumerate(affected_methods[:10], 1):
                        class_name = method.get("class_name", "Unknown")
                        method_name = method.get("method_name", "Unknown")
                        severity = method.get("severity", "Unknown")
                        lines.append(f"{j}. `{class_name}.{method_name}` - 严重程度: {severity}\n")
                    if len(affected_methods) > 10:
                        lines.append(f"\n... 还有 {len(affected_methods) - 10} 个方法\n")

                if impact_graph:
                    lines.append("#### 影响图统计\n")
                    nodes = impact_graph.get("nodes", [])
                    edges = impact_graph.get("edges", [])
                    lines.append(f"- 总节点数: {len(nodes)}\n")
                    lines.append(f"- 总边数: {len(edges)}\n")
                    lines.append("\n")

            except Exception as e:
                lines.append(f"⚠ 数据解析错误: {e}\n")
        else:
            lines.append("### 分析状态\n")
            error = analysis_result.get("error", "Unknown error")
            lines.append(f"❌ 分析失败: {error}\n")

        lines.append("---\n\n")

    # 添加汇总
    lines.append("## 分析汇总\n\n")
    lines.append(f"- 总分析提交数: {len(analysis_results)}\n")
    lines.append(f"- 成功分析数: {successful_analyses}\n")
    lines.append(f"- 失败分析数: {len(analysis_results) - successful_analyses}\n")
    lines.append(f"- 总Java文件变更: {total_java_files}\n")
    lines.append(f"- 总受影响方法数: {total_affected_methods}\n")
    if successful_analyses > 0:
        lines.append(f"- 平均每个提交受影响方法: {total_affected_methods / successful_analyses:.1f}\n")

    return "\n".join(lines)


def main():
    """主函数"""
    print("=" * 80)
    print("JCIA Jenkins代码影响分析演示")
    print("=" * 80 + "\n")

    print(f"开始分析Jenkins代码仓库: {JENKINS_REPO_PATH}")
    print(f"计划分析 {len(JENKINS_COMMITS)} 个提交\n")
    print("\n" + "-" * 80 + "\n")

    results = []

    for commit_info in JENKINS_COMMITS:
        print(f"分析提交: {commit_info['hash']} - {commit_info['message'][:50]}")
        analysis_result = analyze_commit_with_jcia(commit_info['hash'])
        results.append((commit_info, analysis_result))
        print("-" * 80)

    # 生成报告
    print("\n生成分析报告...\n")

    markdown_report = generate_markdown_report(results)

    # 保存报告
    report_path = project_root / "reports" / f"jenkins_impact_analysis_demo.md"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(markdown_report)

    print("=" * 80)
    print("分析完成！")
    print("=" * 80)
    print(f"\n报告已保存到: {report_path}")
    print("\n可以查看以下内容:")
    print("  - 每个提交的详细分析结果")
    print("  - 受影响的方法列表")
    print("  - 影响图统计")
    print("  - 分析汇总")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
