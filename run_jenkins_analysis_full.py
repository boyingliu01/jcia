"""运行 Jenkins 仓库影响分析（完整版，使用 PyDriller）."""
from pathlib import Path

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.adapters.tools.mock_call_chain_analyzer import MockCallChainAnalyzer
from jcia.core.use_cases.analyze_impact import AnalyzeImpactRequest, AnalyzeImpactUseCase
from jcia.reports.base import ReportData
from jcia.reports.html_reporter import HTMLReporter

# 配置
repo_path = str(Path(r"E:\Study\LLM\Java代码变更影响分析\jenkins-full"))
from_commit = "68f5885"  # Fix "Zeno's paradox"
to_commit = "52fa585"    # Replace dependency on jenkins.io

print("=" * 60)
print("Jenkins 代码变更影响分析（完整版）")
print("=" * 60)
print(f"仓库路径: {repo_path}")
print(f"起始提交: {from_commit}")
print(f"结束提交: {to_commit}")
print("-" * 60)

# 创建分析器
print("\n1. 创建分析器...")
analyzer = PyDrillerAdapter(repo_path=repo_path)
call_chain_analyzer = MockCallChainAnalyzer(repo_path=repo_path)
use_case = AnalyzeImpactUseCase(
    change_analyzer=analyzer,
    call_chain_analyzer=call_chain_analyzer,
)
print("  ✓ 分析器创建成功")

# 创建请求
print("\n2. 创建分析请求...")
request = AnalyzeImpactRequest(
    repo_path=Path(repo_path),
    from_commit=from_commit,
    to_commit=to_commit,
    max_depth=5,
    include_test_files=True,
)
print("  ✓ 请求创建成功")

# 执行分析
print("\n3. 执行影响分析...")
try:
    response = use_case.execute(request)
    print("  ✓ 分析完成")

    # 输出摘要
    print("\n" + "=" * 60)
    print("分析摘要")
    print("=" * 60)
    print(f"变更提交数: {response.change_set.commit_count}")
    print(f"变更文件数: {len(response.change_set.changed_files)}")
    print(f"变更Java文件数: {len(response.change_set.changed_java_files)}")
    print(f"变更方法数: {len(response.change_set.changed_methods)}")
    print(f"总新增行数: {response.change_set.total_insertions}")
    print(f"总删除行数: {response.change_set.total_deletions}")
    print("-" * 60)

    if response.impact_graph:
        print(f"受影响方法数: {response.impact_graph.total_affected_methods}")
        print(f"直接影响数: {response.impact_graph.direct_impact_count}")
        print(f"间接影响数: {response.impact_graph.indirect_impact_count}")
        print(f"高风险变更数: {response.impact_graph.high_severity_count}")
        print(f"受影响类数: {len(response.impact_graph.affected_classes)}")
        print("-" * 60)

    # 显示变更文件
    print("\n变更的文件:")
    for i, file_path in enumerate(response.change_set.changed_files[:20], 1):
        file_change = response.change_set.get_file_change(file_path)
        if file_change:
            print(f"  {i}. {file_path} ({file_change.change_type.value}, +{file_change.insertions}/-{file_change.deletions})")
        else:
            print(f"  {i}. {file_path}")

    # 显示变更方法
    if response.change_set.changed_methods:
        print(f"\n变更的方法 (共{len(response.change_set.changed_methods)}个):")
        for i, method_name in enumerate(response.change_set.changed_methods[:20], 1):
            print(f"  {i}. {method_name}")

    # 显示受影响的方法
    if response.impact_graph and response.impact_graph.nodes:
        print(f"\n受影响的方法 (共{response.impact_graph.total_affected_methods}个):")
        for i, (method_name, node) in enumerate(list(response.impact_graph.nodes.items())[:20], 1):
            print(f"  {i}. {method_name} ({node.impact_type.value}, {node.severity.value})")

    # 生成HTML报告
    print("\n4. 生成HTML报告...")
    reporter = HTMLReporter(output_dir=Path(r"E:\Study\LLM\Java代码变更影响分析\report"))

    data = ReportData(
        title="Jenkins 代码变更影响分析报告（完整版）",
        test_run=None,
        impact_graph=response.impact_graph,
        change_set=response.change_set,
        comparison=None,
        metadata={
            "repo_path": str(repo_path),
            "from_commit": from_commit,
            "to_commit": to_commit,
            "max_depth": request.max_depth,
        },
    )

    result = reporter.generate(data)

    if result.success:
        print("  ✓ HTML报告已生成")
        print(f"    路径: {result.output_path}")
        print(f"    大小: {result.size_bytes} 字节")
    else:
        print(f"  ✗ 报告生成失败: {result.error_message}")

    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)

except Exception as e:
    print(f"  ✗ 分析失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
