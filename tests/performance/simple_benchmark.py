"""简单的性能基准测试."""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from jcia.adapters.tools.source_code_call_graph_adapter import SourceCodeCallGraphAnalyzer


def benchmark_project_scan(repo_path: Path) -> dict:
    """测试项目扫描性能.

    Args:
        repo_path: 仓库路径

    Returns:
        性能指标
    """
    print(f"\n测试项目扫描: {repo_path}")

    start_time = time.perf_counter()
    start_cpu = time.process_time()

    try:
        # 初始化分析器（这会扫描整个项目）
        analyzer = SourceCodeCallGraphAnalyzer(
            str(repo_path),
            max_depth=5,
        )

        end_cpu = time.process_time()
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000
        cpu_time_ms = (end_cpu - start_cpu) * 1000

        # 获取统计信息
        java_files = list(repo_path.rglob("*.java"))
        cached_classes = len(analyzer._class_methods_cache)
        cached_methods = sum(
            len(methods) for methods in analyzer._class_methods_cache.values()
        )

        result = {
            "success": True,
            "duration_ms": duration_ms,
            "cpu_time_ms": cpu_time_ms,
            "java_files": len(java_files),
            "cached_classes": cached_classes,
            "cached_methods": cached_methods,
            "files_per_second": len(java_files) / (duration_ms / 1000) if duration_ms > 0 else 0,
        }

        print(f"  成功!")
        print(f"  持续时间: {duration_ms:.2f} ms")
        print(f"  CPU时间: {cpu_time_ms:.2f} ms")
        print(f"  Java文件数: {len(java_files)}")
        print(f"  缓存类数: {cached_classes}")
        print(f"  缓存方法数: {cached_methods}")
        print(f"  处理速度: {result['files_per_second']:.2f} files/sec")

        return result

    except Exception as e:
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        print(f"  失败: {e}")

        return {
            "success": False,
            "duration_ms": duration_ms,
            "error": str(e),
        }


def main() -> int:
    """主函数."""
    print("=" * 80)
    print("JCIA性能基准测试")
    print("=" * 80)

    # 测试路径
    test_paths = [
        Path("./jenkins"),
        Path("./tests/test_data/jenkins_test_repo"),
        Path("."),  # 自身项目
    ]

    all_results = []

    for test_path in test_paths:
        if test_path.exists() and any(test_path.rglob("*.java")):
            result = benchmark_project_scan(test_path)
            result["test_path"] = str(test_path)
            all_results.append(result)
            print()
        else:
            print(f"跳过 {test_path}: 不存在或没有Java文件\n")

    # 汇总报告
    print("=" * 80)
    print("测试汇总")
    print("=" * 80)

    successful = [r for r in all_results if r.get("success")]
    failed = [r for r in all_results if not r.get("success")]

    print(f"总测试数: {len(all_results)}")
    print(f"成功: {len(successful)}")
    print(f"失败: {len(failed)}")

    if successful:
        print("\n成功的测试:")
        for r in successful:
            print(f"  {r['test_path']}:")
            print(f"    持续时间: {r['duration_ms']:.2f} ms")
            print(f"    Java文件: {r.get('java_files', 'N/A')}")

    if failed:
        print("\n失败的测试:")
        for r in failed:
            print(f"  {r.get('test_path', 'Unknown')}: {r.get('error', 'Unknown error')}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
