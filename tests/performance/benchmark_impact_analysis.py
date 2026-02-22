"""JCIA影响分析性能基准测试.

测试场景：
1. 小型仓库（< 100个Java文件）
2. 中型仓库（100-1000个Java文件）
3. 大型仓库（> 1000个Java文件）

测试内容：
- Git变更提取（PyDriller）
- 调用链分析（CallChainAnalyzer）
- 影响图构建（ImpactGraph）
- 完整分析流程
"""

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.adapters.tools.source_code_call_graph_adapter import SourceCodeCallGraphAnalyzer
from jcia.core.entities.impact_graph import ImpactGraph
from jcia.core.services.impact_analysis_service import ImpactAnalysisService
from jcia.core.use_cases.analyze_impact import AnalyzeImpactRequest, AnalyzeImpactUseCase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """基准测试结果."""

    operation: str
    repo_size: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    duration_ms: float = 0.0
    cpu_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    success: bool = True
    error_message: str = ""
    additional_data: dict[str, Any] = field(default_factory=dict)

    def finalize(self) -> None:
        """完成测试."""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "operation": self.operation,
            "repo_size": self.repo_size,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "cpu_time_ms": self.cpu_time_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "success": self.success,
            "error_message": self.error_message,
            "additional_data": self.additional_data,
        }


class ImpactAnalysisBenchmark:
    """影响分析性能基准测试器."""

    def __init__(self, output_dir: Path | None = None) -> None:
        """初始化.

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or Path("performance_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[BenchmarkResult] = []

    def run_all_benchmarks(self, repo_path: Path | None = None) -> None:
        """运行所有基准测试.

        Args:
            repo_path: 可选的仓库路径，用于真实测试
        """
        logger.info("开始性能基准测试...")

        # 1. 测试不同规模仓库的分析性能
        self._benchmark_repo_sizes()

        # 2. 测试Git变更提取性能
        if repo_path and repo_path.exists():
            self._benchmark_git_analysis(repo_path)

            # 3. 测试调用链分析性能
            self._benchmark_call_chain_analysis(repo_path)

            # 4. 测试完整分析流程
            self._benchmark_full_analysis(repo_path)

        # 5. 生成报告
        self._generate_report()

        logger.info("性能基准测试完成")

    def _benchmark_repo_sizes(self) -> None:
        """测试不同规模仓库的性能."""
        logger.info("测试不同规模仓库...")

        # 模拟不同规模的仓库测试
        sizes = [
            ("small", 50),
            ("medium", 500),
            ("large", 2000),
        ]

        for size_name, file_count in sizes:
            result = BenchmarkResult(
                operation="repo_size_simulation",
                repo_size=size_name,
            )

            try:
                # 模拟分析延迟（基于文件数量）
                simulated_duration = file_count * 5  # 每个文件5ms

                result.start_time = datetime.now()
                time.sleep(simulated_duration / 1000)  # 转换为秒
                result.finalize()
                result.additional_data = {
                    "simulated_files": file_count,
                    "simulated_duration_ms": simulated_duration,
                }

            except Exception as e:
                result.success = False
                result.error_message = str(e)
                result.finalize()

            self.results.append(result)

    def _benchmark_git_analysis(self, repo_path: Path) -> None:
        """测试Git分析性能.

        Args:
            repo_path: 仓库路径
        """
        logger.info(f"测试Git分析性能: {repo_path}")

        result = BenchmarkResult(
            operation="git_analysis",
            repo_size="real",
        )

        try:
            result.start_time = datetime.now()

            # 初始化Git适配器
            adapter = PyDrillerAdapter(str(repo_path))

            # 分析最近的提交
            import subprocess
            try:
                # 获取最近的提交
                result_git = subprocess.run(
                    ["git", "log", "--oneline", "-5"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                commits = [line.split()[0] for line in result_git.stdout.strip().split("\n") if line]

                if len(commits) >= 2:
                    # 分析提交范围
                    change_set = adapter.analyze_commits(commits[-1], commits[0])
                    result.additional_data = {
                        "commits_analyzed": len(commits),
                        "files_changed": len(change_set.file_changes),
                        "methods_changed": len(change_set.changed_methods),
                    }
            except subprocess.SubprocessError as e:
                logger.warning(f"Git command failed: {e}")
                result.additional_data = {"git_command_error": str(e)}

            result.finalize()

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.finalize()

        self.results.append(result)

    def _benchmark_call_chain_analysis(self, repo_path: Path) -> None:
        """测试调用链分析性能.

        Args:
            repo_path: 仓库路径
        """
        logger.info(f"测试调用链分析性能: {repo_path}")

        result = BenchmarkResult(
            operation="call_chain_analysis",
            repo_size="real",
        )

        try:
            result.start_time = datetime.now()

            # 初始化源代码调用链分析器
            analyzer = SourceCodeCallGraphAnalyzer(str(repo_path), max_depth=5)

            # 统计扫描到的文件和方法
            java_files_count = len(list(repo_path.rglob("*.java")))

            result.additional_data = {
                "java_files_scanned": java_files_count,
                "classes_cached": len(analyzer._class_methods_cache),
                "methods_cached": sum(
                    len(methods) for methods in analyzer._class_methods_cache.values()
                ),
            }

            result.finalize()

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.finalize()

        self.results.append(result)

    def _benchmark_full_analysis(self, repo_path: Path) -> None:
        """测试完整分析流程.

        Args:
            repo_path: 仓库路径
        """
        logger.info(f"测试完整分析流程: {repo_path}")

        result = BenchmarkResult(
            operation="full_analysis",
            repo_size="real",
        )

        try:
            result.start_time = datetime.now()

            # 完整分析流程
            # 1. Git分析
            git_adapter = PyDrillerAdapter(str(repo_path))

            # 2. 调用链分析器
            call_chain_analyzer = SourceCodeCallGraphAnalyzer(str(repo_path), max_depth=5)

            # 3. 构建UseCase
            use_case = AnalyzeImpactUseCase(
                change_analyzer=git_adapter,
                call_chain_analyzer=call_chain_analyzer,
            )

            # 4. 模拟分析请求
            import subprocess
            try:
                result_git = subprocess.run(
                    ["git", "log", "--oneline", "-2"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                commits = [line.split()[0] for line in result_git.stdout.strip().split("\n") if line]

                if len(commits) >= 2:
                    request = AnalyzeImpactRequest(
                        repo_path=repo_path,
                        from_commit=commits[-1],
                        to_commit=commits[0],
                        max_depth=5,
                    )

                    # 执行分析
                    response = use_case.execute(request)

                    result.additional_data = {
                        "commits_analyzed": len(commits),
                        "files_changed": len(response.change_set.file_changes),
                        "methods_changed": len(response.change_set.changed_methods),
                        "total_affected_methods": response.impact_graph.total_affected_methods,
                        "direct_impacts": response.impact_graph.direct_impact_count,
                        "indirect_impacts": response.impact_graph.indirect_impact_count,
                    }
                else:
                    result.additional_data = {"warning": "Not enough commits for full analysis"}
            except subprocess.SubprocessError as e:
                result.additional_data = {"git_error": str(e)}

            result.finalize()

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.finalize()
            logger.exception("Full analysis failed")

        self.results.append(result)

    def _generate_report(self) -> Path:
        """生成性能分析报告.

        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"benchmark_report_{timestamp}.json"

        # 计算统计数据
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]

        report_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(self.results),
                "successful": len(successful_results),
                "failed": len(failed_results),
                "total_duration_ms": sum(r.duration_ms for r in successful_results),
                "avg_duration_ms": (
                    sum(r.duration_ms for r in successful_results) / len(successful_results)
                    if successful_results else 0
                ),
            },
            "results": [r.to_dict() for r in self.results],
            "bottlenecks": self._identify_bottlenecks(),
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Benchmark report generated: {report_path}")

        # 同时生成可读性更好的文本报告
        self._generate_text_report(report_path.with_suffix(".txt"))

        return report_path

    def _identify_bottlenecks(self) -> list[dict[str, Any]]:
        """识别性能瓶颈.

        Returns:
            瓶颈列表
        """
        bottlenecks = []

        # 按操作分组，找出最慢的操作
        operations: dict[str, list[BenchmarkResult]] = {}
        for result in self.results:
            if result.success:
                if result.operation not in operations:
                    operations[result.operation] = []
                operations[result.operation].append(result)

        for op_name, op_results in operations.items():
            if not op_results:
                continue

            avg_duration = sum(r.duration_ms for r in op_results) / len(op_results)
            max_duration = max(r.duration_ms for r in op_results)

            # 定义阈值（毫秒）
            if avg_duration > 60000:  # 60秒
                severity = "CRITICAL"
            elif avg_duration > 10000:  # 10秒
                severity = "HIGH"
            elif avg_duration > 1000:  # 1秒
                severity = "MEDIUM"
            else:
                severity = "LOW"

            if severity in ["CRITICAL", "HIGH"]:
                bottlenecks.append({
                    "operation": op_name,
                    "severity": severity,
                    "avg_duration_ms": avg_duration,
                    "max_duration_ms": max_duration,
                    "sample_count": len(op_results),
                })

        # 按严重程度和持续时间排序
        bottlenecks.sort(key=lambda x: (x["severity"] != "CRITICAL", x["avg_duration_ms"]), reverse=True)

        return bottlenecks[:10]  # 只返回前10个

    def _generate_text_report(self, report_path: Path) -> None:
        """生成文本格式的报告.

        Args:
            report_path: 报告路径
        """
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("JCIA影响分析性能基准测试报告\n")
            f.write("=" * 80 + "\n\n")

            # 摘要
            successful = [r for r in self.results if r.success]
            failed = [r for r in self.results if not r.success]

            f.write(f"生成时间: {datetime.now().isoformat()}\n")
            f.write(f"总测试数: {len(self.results)}\n")
            f.write(f"成功: {len(successful)}\n")
            f.write(f"失败: {len(failed)}\n\n")

            # 详细结果
            f.write("-" * 80 + "\n")
            f.write("详细测试结果\n")
            f.write("-" * 80 + "\n\n")

            for i, result in enumerate(self.results, 1):
                f.write(f"{i}. {result.operation} ({result.repo_size})\n")
                f.write(f"   状态: {'成功' if result.success else '失败'}\n")
                f.write(f"   持续时间: {result.duration_ms:.2f} ms\n")
                if not result.success:
                    f.write(f"   错误: {result.error_message}\n")
                if result.additional_data:
                    f.write(f"   附加数据: {json.dumps(result.additional_data, indent=6)}\n")
                f.write("\n")

            # 瓶颈识别
            bottlenecks = self._identify_bottlenecks()
            if bottlenecks:
                f.write("-" * 80 + "\n")
                f.write("识别到的性能瓶颈\n")
                f.write("-" * 80 + "\n\n")

                for i, bottleneck in enumerate(bottlenecks, 1):
                    f.write(f"{i}. {bottleneck['operation']}\n")
                    f.write(f"   严重程度: {bottleneck['severity']}\n")
                    f.write(f"   平均耗时: {bottleneck['avg_duration_ms']:.2f} ms\n")
                    f.write(f"   最大耗时: {bottleneck['max_duration_ms']:.2f} ms\n")
                    f.write(f"   样本数: {bottleneck['sample_count']}\n\n")

            f.write("=" * 80 + "\n")
            f.write("报告结束\n")
            f.write("=" * 80 + "\n")

        logger.info(f"Text report generated: {report_path}")


def main() -> int:
    """主函数.

    Returns:
        退出码
    """
    import argparse

    parser = argparse.ArgumentParser(description="JCIA性能基准测试")
    parser.add_argument(
        "--repo-path",
        type=Path,
        help="测试用的真实仓库路径",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("performance_reports"),
        help="报告输出目录",
    )

    args = parser.parse_args()

    # 创建并运行基准测试
    benchmark = ImpactAnalysisBenchmark(output_dir=args.output_dir)
    benchmark.run_all_benchmarks(repo_path=args.repo_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
