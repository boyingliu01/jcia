#!/usr/bin/env python
"""Generate impact analysis report for Jenkins commit using local analysis."""

import subprocess
from datetime import datetime
from pathlib import Path

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.adapters.tools.source_code_call_graph_adapter import (
    SourceCodeCallGraphAnalyzer,
)


def main():
    # Commit to analyze: Fix temporary offline state of computer is lost on config submit
    commit_hash = "acc742d9cb"

    # Build output lines
    lines = []

    lines.append("=" * 80)
    lines.append("              Java 代码影响范围分析报告")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Get commit info
    result = subprocess.run(
        ["git", "show", commit_hash, "--format=%H|%an|%s", "-s"],
        cwd="./jenkins",
        capture_output=True,
        text=True,
    )
    commit_info = result.stdout.strip().split("|")
    commit_full_hash = commit_info[0]
    commit_author = commit_info[1]
    commit_msg = commit_info[2]

    lines.append("+-" + "-" * 76 + "-+")
    lines.append("| 提交信息".center(76) + "|")
    lines.append("+-" + "-" * 76 + "-+")
    lines.append(f"| Hash:    {commit_full_hash[:12]:<68}|")
    lines.append(f"| 作者:    {commit_author:<68}|")
    lines.append(f"| 消息:    {commit_msg[:68]:<68}|")
    lines.append("+-" + "-" * 76 + "-+")
    lines.append("")

    # Initialize adapters
    git_adapter = PyDrillerAdapter(repo_path="./jenkins")
    call_chain_adapter = SourceCodeCallGraphAnalyzer(
        repo_path="./jenkins", max_depth=5
    )

    lines.append("+-" + "-" * 76 + "-+")
    lines.append("| 分析器信息".center(76) + "|")
    lines.append("+-" + "-" * 76 + "-+")
    lines.append("| 仓库:            ./jenkins                                      |")
    class_count = len(call_chain_adapter._class_methods_cache)
    lines.append(f"| Java 类数量:     {class_count:<60}|")
    call_count = len(call_chain_adapter._method_calls_cache)
    lines.append(f"| 方法调用追踪:    {call_count} 个类                                |")
    lines.append("+-" + "-" * 76 + "-+")
    lines.append("")

    # Get changes
    changes = git_adapter.analyze_commit_range(f"{commit_hash}^..{commit_hash}")

    lines.append("+-" + "-" * 76 + "-+")
    lines.append("| 变更摘要".center(76) + "|")
    lines.append("+-" + "-" * 76 + "-+")
    lines.append(f"| 变更文件数:      {len(changes.file_changes):<60}|")
    lines.append(f"| Java 文件:       {len(changes.changed_java_files):<60}|")
    lines.append(f"| 新增行数:        {changes.total_insertions:<60}|")
    lines.append(f"| 删除行数:        {changes.total_deletions:<60}|")
    lines.append("+-" + "-" * 76 + "-+")
    lines.append("")

    lines.append("+-" + "-" * 76 + "-+")
    lines.append("| 变更文件列表".center(76) + "|")
    lines.append("+-" + "-" * 76 + "-+")
    for fc in changes.file_changes:
        filename = fc.file_path.split("/")[-1]
        lines.append(f"| {filename:<74}|")
        lines.append(f"|   路径: {fc.file_path:<70}|")
        lines.append(f"|   类型: {fc.change_type.name:<70}|")
    lines.append("+-" + "-" * 76 + "-+")
    lines.append("")

    # Analyze class dependencies - find the Java class
    # Handle simple filenames (shallow clone) vs full paths
    java_classes = []
    for fc in changes.file_changes:
        if str(fc.file_path).endswith(".java"):
            # Simple name like Computer.java
            simple_name = str(fc.file_path)[:-5]  # Remove .java

            # Search in cache for matching class
            for cached_class in call_chain_adapter._class_methods_cache.keys():
                if simple_name.lower() == cached_class.split(".")[-1].lower():
                    if cached_class not in java_classes:
                        java_classes.append(cached_class)

    lines.append("+-" + "-" * 76 + "-+")
    lines.append("| 类依赖分析".center(76) + "|")
    lines.append("+-" + "-" * 76 + "-+")

    for java_class in java_classes:
        lines.append("")
        lines.append(f"| 类: {java_class:<69}|")
        lines.append("+-" + "-" * 76 + "-+")
        deps = call_chain_adapter.analyze_class_dependencies(java_class)
        lines.append(f"| 依赖其他类:      {len(deps.get('dependencies', [])):<60}|")
        lines.append(f"| 被依赖(调用者):  {len(deps.get('dependents', [])):<60}|")

        # Show some dependents
        if deps.get("dependents"):
            lines.append("+-" + "-" * 76 + "-+")
            lines.append("| 依赖该类的部分类 (前10个)".center(76) + "|")
            lines.append("+-" + "-" * 76 + "-+")
            for dep in deps["dependents"][:10]:
                lines.append(f"| {dep:<74}|")
            lines.append("+-" + "-" * 76 + "-+")

        # Find test classes
        lines.append("")
        lines.append("| 相关测试类".center(76) + "|")
        lines.append("+-" + "-" * 76 + "-+")
        test_patterns = [java_class.split(".")[-1] + "Test", "Test" + java_class.split(".")[-1]]
        found_tests = []
        for pattern in test_patterns:
            for known_class in call_chain_adapter._class_methods_cache:
                if pattern.lower() in known_class.lower() and "test" in known_class.lower():
                    if known_class not in found_tests:
                        found_tests.append(known_class)

        if found_tests:
            for t in found_tests[:5]:
                lines.append(f"| {t:<74}|")
        else:
            lines.append("| 未找到直接匹配的测试类                                  |")
        lines.append("+-" + "-" * 76 + "-+")

    lines.append("")
    lines.append("=" * 80)
    lines.append("                    分析完成".center(80))
    lines.append("=" * 80)

    # Print to console
    output = "\n".join(lines)
    print(output)

    # Save to report directory
    report_dir = Path("./report")
    report_dir.mkdir(exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    commit_short = commit_full_hash[:8]
    report_file = report_dir / f"impact_analysis_{commit_short}_{timestamp}.md"

    # Write to file
    report_file.write_text(output, encoding="utf-8")
    print(f"\n报告已保存到: {report_file}")


if __name__ == "__main__":
    main()
