#!/usr/bin/env python
"""Generate impact analysis report for Jenkins commit using local analysis."""

import subprocess
from pathlib import Path

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.adapters.tools.source_code_call_graph_adapter import (
    SourceCodeCallGraphAnalyzer,
)


def main():
    # Commit to analyze: Fix temporary offline state of computer is lost on config submit
    commit_hash = "acc742d9cb"

    print("=" * 80)
    print("              Java 代码影响范围分析报告")
    print("=" * 80)
    print()

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

    print("+-" + "-" * 76 + "-+")
    print("| 提交信息".center(76) + "|")
    print("+-" + "-" * 76 + "-+")
    print(f"| Hash:    {commit_full_hash[:12]:<68}|")
    print(f"| 作者:    {commit_author:<68}|")
    print(f"| 消息:    {commit_msg[:68]:<68}|")
    print("+-" + "-" * 76 + "-+")
    print()

    # Initialize adapters
    git_adapter = PyDrillerAdapter(repo_path="./jenkins")
    call_chain_adapter = SourceCodeCallGraphAnalyzer(
        repo_path="./jenkins", max_depth=5
    )

    print("+-" + "-" * 76 + "-+")
    print("| 分析器信息".center(76) + "|")
    print("+-" + "-" * 76 + "-+")
    print("| 仓库:            ./jenkins                                      |")
    class_count = len(call_chain_adapter._class_methods_cache)
    print(f"| Java 类数量:     {class_count:<60}|")
    call_count = len(call_chain_adapter._method_calls_cache)
    print(f"| 方法调用追踪:    {call_count} 个类                                |")
    print("+-" + "-" * 76 + "-+")
    print()

    # Get changes
    changes = git_adapter.analyze_commit_range(f"{commit_hash}^..{commit_hash}")

    print("+-" + "-" * 76 + "-+")
    print("| 变更摘要".center(76) + "|")
    print("+-" + "-" * 76 + "-+")
    print(f"| 变更文件数:      {len(changes.file_changes):<60}|")
    print(f"| Java 文件:       {len(changes.changed_java_files):<60}|")
    print(f"| 新增行数:        {changes.total_insertions:<60}|")
    print(f"| 删除行数:        {changes.total_deletions:<60}|")
    print("+-" + "-" * 76 + "-+")
    print()

    print("+-" + "-" * 76 + "-+")
    print("| 变更文件列表".center(76) + "|")
    print("+-" + "-" * 76 + "-+")
    for fc in changes.file_changes:
        filename = fc.file_path.split("/")[-1]
        print(f"| {filename:<74}|")
        print(f"|   路径: {fc.file_path:<70}|")
        print(f"|   类型: {fc.change_type.name:<70}|")
    print("+-" + "-" * 76 + "-+")
    print()

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

    print("+-" + "-" * 76 + "-+")
    print("| 类依赖分析".center(76) + "|")
    print("+-" + "-" * 76 + "-+")

    for java_class in java_classes:
        print(f"\n| 类: {java_class:<69}|")
        print("+-" + "-" * 76 + "-+")
        deps = call_chain_adapter.analyze_class_dependencies(java_class)
        print(f"| 依赖其他类:      {len(deps.get('dependencies', [])):<60}|")
        print(f"| 被依赖(调用者):  {len(deps.get('dependents', [])):<60}|")

        # Show some dependents
        if deps.get("dependents"):
            print("+-" + "-" * 76 + "-+")
            print("| 依赖该类的部分类 (前10个)".center(76) + "|")
            print("+-" + "-" * 76 + "-+")
            for dep in deps["dependents"][:10]:
                print(f"| {dep:<74}|")
            print("+-" + "-" * 76 + "-+")

        # Find test classes
        print("\n| 相关测试类".center(76) + "|")
        print("+-" + "-" * 76 + "-+")
        test_patterns = [java_class.split(".")[-1] + "Test", "Test" + java_class.split(".")[-1]]
        found_tests = []
        for pattern in test_patterns:
            for known_class in call_chain_adapter._class_methods_cache:
                if pattern.lower() in known_class.lower() and "test" in known_class.lower():
                    if known_class not in found_tests:
                        found_tests.append(known_class)

        if found_tests:
            for t in found_tests[:5]:
                print(f"| {t:<74}|")
        else:
            print("| 未找到直接匹配的测试类                                  |")
        print("+-" + "-" * 76 + "-+")

    print()
    print("=" * 80)
    print("                    分析完成".center(80))
    print("=" * 80)


if __name__ == "__main__":
    main()
