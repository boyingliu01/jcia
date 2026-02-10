"""运行 Jenkins 仓库影响分析（使用 git show 命令）."""
import subprocess
from datetime import datetime
from pathlib import Path

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.adapters.tools.mock_call_chain_analyzer import MockCallChainAnalyzer
from jcia.core.entities.change_set import (
    ChangeSet,
    ChangeStatus,
    ChangeType,
    CommitInfo,
    FileChange,
)
from jcia.core.services.impact_analysis_service import ImpactAnalysisService
from jcia.reports.base import ReportData
from jcia.reports.html_reporter import HTMLReporter

# 配置
repo_path = str(Path(r"E:\Study\LLM\Java代码变更影响分析\jenkins-full"))
from_commit = "68f5885"  # Fix "Zeno's paradox"
to_commit = "52fa585"    # Replace dependency on jenkins.io

print("=" * 60)
print("Jenkins 代码变更影响分析")
print("=" * 60)
print(f"仓库路径: {repo_path}")
print(f"起始提交: {from_commit}")
print(f"结束提交: {to_commit}")
print("-" * 60)

# 使用 git log 命令获取提交范围内的信息
print("\n1. 获取提交范围信息...")
try:
    # 获取起始提交信息
    result_from = subprocess.run(
        ["git", "show", "--no-patch", "--format=%H|%an|%ae|%ai|%s", from_commit],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    parts = result_from.stdout.strip().split("|")
    from_full_hash, from_author_name, from_author_email, from_author_date, from_commit_message = parts

    print("  ✓ 起始提交信息获取成功")
    print(f"    作者: {from_author_name}")
    print(f"    时间: {from_author_date}")
    print(f"    消息: {from_commit_message[:60]}...")

    # 获取结束提交信息
    result_to = subprocess.run(
        ["git", "show", "--no-patch", "--format=%H|%an|%ae|%ai|%s", to_commit],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    parts = result_to.stdout.strip().split("|")
    to_full_hash, to_author_name, to_author_email, to_author_date, to_commit_message = parts

    print("  ✓ 结束提交信息获取成功")
    print(f"    作者: {to_author_name}")
    print(f"    时间: {to_author_date}")
    print(f"    消息: {to_commit_message[:60]}...")

except Exception as e:
    print(f"  ✗ 获取提交信息失败: {e}")
    exit(1)

# 获取文件变更列表
print("\n2. 获取文件变更...")
try:
    result = subprocess.run(
        ["git", "log", f"{from_commit}..{to_commit}", "--name-only", "--pretty=format:"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    file_paths = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    print(f"  ✓ 找到 {len(file_paths)} 个变更文件")

except Exception as e:
    print(f"  ✗ 获取文件变更失败: {e}")
    exit(1)

# 创建分析器
print("\n3. 创建分析器...")
analyzer = PyDrillerAdapter(repo_path=repo_path)
call_chain_analyzer = MockCallChainAnalyzer(repo_path=repo_path)
print("  ✓ 分析器创建成功")

# 手动构建 ChangeSet
print("\n4. 构建变更集合...")
try:
    # 为起始提交创建 CommitInfo
    from_commit_info = CommitInfo(
        hash=from_full_hash,
        message=from_commit_message,
        author=from_author_name,
        email=from_author_email,
        timestamp=datetime.fromisoformat(from_author_date.replace(" +", "+")),
        parents=[],
    )

    # 为结束提交创建 CommitInfo
    to_commit_info = CommitInfo(
        hash=to_full_hash,
        message=to_commit_message,
        author=to_author_name,
        email=to_author_email,
        timestamp=datetime.fromisoformat(to_author_date.replace(" +", "+")),
        parents=[from_full_hash],
    )

    change_set = ChangeSet(
        from_commit=from_full_hash,
        to_commit=to_full_hash,
        commits=[from_commit_info, to_commit_info],
        file_changes=[],
        status=ChangeStatus.COMMITTED,
    )

    # 添加文件变更
    for file_path in file_paths:
        if file_path.endswith(".java"):
            file_change = FileChange(
                file_path=file_path,
                change_type=ChangeType.MODIFY,  # 假设都是修改
                insertions=0,  # 暂不统计
                deletions=0,
            )
            change_set.add_file_change(file_change)

    print("  ✓ 变更集合构建成功")
    print(f"    - 文件数: {len(change_set.changed_files)}")
    print(f"    - Java文件数: {len(change_set.changed_java_files)}")

except Exception as e:
    print(f"  ✗ 构建变更集合失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 执行影响分析
print("\n5. 执行影响分析...")
try:
    impact_service = ImpactAnalysisService(call_chain_analyzer=call_chain_analyzer)
    impact_graph = impact_service.analyze(change_set, max_depth=5)

    print("  ✓ 影响分析完成")
    print(f"    - 受影响方法数: {impact_graph.total_affected_methods}")
    print(f"    - 直接影响数: {impact_graph.direct_impact_count}")
    print(f"    - 间接影响数: {impact_graph.indirect_impact_count}")
    print(f"    - 高风险变更数: {impact_graph.high_severity_count}")
    print(f"    - 受影响类数: {len(impact_graph.affected_classes)}")

except Exception as e:
    print(f"  ✗ 影响分析失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 显示摘要
print("\n" + "=" * 60)
print("分析摘要")
print("=" * 60)
print(f"变更提交数: {change_set.commit_count}")
print(f"变更文件数: {len(change_set.changed_files)}")
print(f"变更Java文件数: {len(change_set.changed_java_files)}")
print(f"变更方法数: {len(change_set.changed_methods)}")
print(f"总新增行数: {change_set.total_insertions}")
print(f"总删除行数: {change_set.total_deletions}")
print("-" * 60)

# 显示前10个变更的Java文件
print("\n前10个变更的Java文件:")
for i, file_path in enumerate(change_set.changed_java_files[:10], 1):
    print(f"  {i}. {file_path}")

# 显示前10个受影响的方法
if impact_graph and impact_graph.nodes:
    print("\n前10个受影响的方法:")
    for i, (method_name, node) in enumerate(list(impact_graph.nodes.items())[:10], 1):
        print(f"  {i}. {method_name} ({node.impact_type.value}, {node.severity.value})")

# 生成HTML报告
print("\n6. 生成HTML报告...")
try:
    reporter = HTMLReporter(output_dir=Path(r"E:\Study\LLM\Java代码变更影响分析\report"))

    data = ReportData(
        title="Jenkins 代码变更影响分析报告",
        test_run=None,
        impact_graph=impact_graph,
        change_set=change_set,
        comparison=None,
        metadata={
            "repo_path": str(repo_path),
            "from_commit": from_full_hash,
            "to_commit": to_full_hash,
            "max_depth": 5,
            "from_commit_message": from_commit_message,
            "to_commit_message": to_commit_message,
            "from_author": f"{from_author_name} <{from_author_email}>",
            "to_author": f"{to_author_name} <{to_author_email}>",
        },
    )

    result = reporter.generate(data)

    if result.success:
        print("  ✓ HTML报告已生成")
        print(f"    路径: {result.output_path}")
        print(f"    大小: {result.size_bytes} 字节")
    else:
        print(f"  ✗ 报告生成失败: {result.error_message}")

except Exception as e:
    print(f"  ✗ 生成报告失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("分析完成！")
print("=" * 60)
