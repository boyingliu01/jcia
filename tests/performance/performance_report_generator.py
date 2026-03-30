"""性能测试报告生成器.

基于性能测试结果生成详细的分析报告。
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class PerformanceReport:
    """性能分析报告."""

    # 执行摘要
    executive_summary: dict[str, Any]

    # 基准测试结果
    benchmark_results: list[dict[str, Any]]

    # 性能瓶颈分析
    bottlenecks: list[dict[str, Any]]

    # 优化方案
    optimization_recommendations: list[dict[str, Any]]

    # 优化实施计划
    implementation_plan: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "executive_summary": self.executive_summary,
            "benchmark_results": self.benchmark_results,
            "bottlenecks": self.bottlenecks,
            "optimization_recommendations": self.optimization_recommendations,
            "implementation_plan": self.implementation_plan,
        }


class PerformanceReportGenerator:
    """性能报告生成器."""

    def __init__(self, benchmark_data: list[dict[str, Any]] | None = None) -> None:
        """初始化.

        Args:
            benchmark_data: 基准测试数据
        """
        self.benchmark_data = benchmark_data or []

    def generate_report(self) -> PerformanceReport:
        """生成完整性能报告.

        Returns:
            性能报告
        """
        return PerformanceReport(
            executive_summary=self._generate_executive_summary(),
            benchmark_results=self._analyze_benchmark_results(),
            bottlenecks=self._identify_bottlenecks(),
            optimization_recommendations=self._generate_recommendations(),
            implementation_plan=self._create_implementation_plan(),
        )

    def _generate_executive_summary(self) -> dict[str, Any]:
        """生成执行摘要.

        Returns:
            执行摘要
        """
        successful_tests = [r for r in self.benchmark_data if r.get("success", False)]

        if not successful_tests:
            return {
                "status": "FAILED",
                "message": "所有测试均失败，无法评估性能",
                "meets_requirements": False,
            }

        # 计算关键指标
        durations = [r.get("duration_ms", 0) for r in successful_tests]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)

        # 检查是否满足10分钟要求
        meets_requirement = max_duration <= 600000  # 10分钟 = 600,000ms

        # 识别主要瓶颈
        slow_tests = [r for r in successful_tests if r.get("duration_ms", 0) > 10000]

        return {
            "status": "PASS" if meets_requirement else "ATTENTION",
            "meets_10min_requirement": meets_requirement,
            "total_tests": len(self.benchmark_data),
            "successful_tests": len(successful_tests),
            "avg_duration_ms": avg_duration,
            "max_duration_ms": max_duration,
            "slow_tests_count": len(slow_tests),
            "recommendation": (
                "性能总体良好，符合10分钟要求"
                if meets_requirement
                else "需要优化：存在超过10分钟的处理时间"
            ),
        }

    def _analyze_benchmark_results(self) -> list[dict[str, Any]]:
        """分析基准测试结果.

        Returns:
            分析后的结果列表
        """
        analyzed = []

        for result in self.benchmark_data:
            analyzed_result = {
                "operation": result.get("test_path", "unknown"),
                "status": "SUCCESS" if result.get("success") else "FAILED",
                "duration_ms": result.get("duration_ms", 0),
                "cpu_time_ms": result.get("cpu_time_ms", 0),
                "files_processed": result.get("java_files", 0),
                "classes_cached": result.get("classes_cached", 0),
                "methods_cached": result.get("methods_cached", 0),
                "processing_speed": result.get("files_per_second", 0),
            }
            analyzed.append(analyzed_result)

        return analyzed

    def _identify_bottlenecks(self) -> list[dict[str, Any]]:
        """识别性能瓶颈.

        Returns:
            瓶颈列表
        """
        bottlenecks = []

        # 分析每个测试结果
        for result in self.benchmark_data:
            if not result.get("success"):
                continue

            duration_ms = result.get("duration_ms", 0)
            test_path = result.get("test_path", "unknown")

            # 根据持续时间判断严重程度
            if duration_ms > 60000:  # > 1分钟
                severity = "CRITICAL"
                description = f"{test_path} 处理时间超过1分钟，严重影响用户体验"
            elif duration_ms > 10000:  # > 10秒
                severity = "HIGH"
                description = f"{test_path} 处理时间超过10秒，需要优化"
            elif duration_ms > 1000:  # > 1秒
                severity = "MEDIUM"
                description = f"{test_path} 处理时间超过1秒，可适当优化"
            else:
                continue  # 不记录低严重度的瓶颈

            bottleneck = {
                "component": test_path,
                "severity": severity,
                "duration_ms": duration_ms,
                "description": description,
                "root_cause": self._analyze_root_cause(result),
            }
            bottlenecks.append(bottleneck)

        # 按严重程度排序
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        bottlenecks.sort(key=lambda x: severity_order.get(x["severity"], 4))

        return bottlenecks[:10]  # 只返回前10个

    def _analyze_root_cause(self, result: dict) -> str:
        """分析瓶颈根本原因.

        Args:
            result: 测试结果

        Returns:
            原因描述
        """
        causes = []

        # 检查文件数量
        java_files = result.get("java_files", 0)
        if java_files > 1000:
            causes.append(f"大型代码库({java_files}个Java文件)")
        elif java_files > 500:
            causes.append(f"中型代码库({java_files}个Java文件)")

        # 检查缓存效率
        classes_cached = result.get("classes_cached", 0)
        methods_cached = result.get("methods_cached", 0)
        if classes_cached > 0 and methods_cached > classes_cached * 100:
            causes.append("大量方法缓存(可能存在缓存冗余)")

        # 检查处理速度
        processing_speed = result.get("files_per_second", 0)
        if processing_speed < 50:
            causes.append(f"低处理速度({processing_speed:.1f} files/sec)")

        return "; ".join(causes) if causes else "未知原因"

    def _generate_recommendations(self) -> list[dict[str, Any]]:
        """生成优化建议.

        Returns:
            优化建议列表
        """
        recommendations = [
            {
                "category": "I/O优化",
                "priority": "HIGH",
                "title": "实现项目扫描缓存机制",
                "description": "当前每次分析都需要重新扫描所有Java文件。建议实现基于文件修改时间的增量扫描缓存。",
                "expected_improvement": "50-70%",
                "implementation_complexity": "MEDIUM",
                "estimated_effort": "3-5天",
            },
            {
                "category": "I/O优化",
                "priority": "HIGH",
                "title": "Git操作批量化",
                "description": "当前Git操作是逐个提交处理的。建议批量获取提交信息，减少I/O次数。",
                "expected_improvement": "30-40%",
                "implementation_complexity": "LOW",
                "estimated_effort": "1-2天",
            },
            {
                "category": "算法优化",
                "priority": "MEDIUM",
                "title": "优化方法调用查找算法",
                "description": "当前使用简单的循环查找。建议使用哈希索引或字典加速方法调用查找。",
                "expected_improvement": "20-30%",
                "implementation_complexity": "MEDIUM",
                "estimated_effort": "2-3天",
            },
            {
                "category": "缓存优化",
                "priority": "HIGH",
                "title": "实现多级缓存策略",
                "description": "实现LRU缓存，缓存分析结果。对于未变更的文件，直接使用缓存结果。",
                "expected_improvement": "60-80%",
                "implementation_complexity": "MEDIUM",
                "estimated_effort": "5-7天",
            },
            {
                "category": "并发优化",
                "priority": "MEDIUM",
                "title": "实现并行文件分析",
                "description": "使用多线程/多进程并行分析Java文件，充分利用多核CPU。",
                "expected_improvement": "40-60% (取决于CPU核心数)",
                "implementation_complexity": "HIGH",
                "estimated_effort": "7-10天",
            },
            {
                "category": "内存优化",
                "priority": "MEDIUM",
                "title": "优化内存使用",
                "description": "当前缓存了大量方法信息，建议实现惰性加载和内存池机制。",
                "expected_improvement": "减少50-70%内存使用",
                "implementation_complexity": "MEDIUM",
                "estimated_effort": "3-5天",
            },
            {
                "category": "进度提示",
                "priority": "LOW",
                "title": "添加分析进度提示",
                "description": "对于长时间运行的分析，提供进度条或阶段性状态更新。",
                "expected_improvement": "提升用户体验",
                "implementation_complexity": "LOW",
                "estimated_effort": "1-2天",
            },
        ]

        return recommendations

    def _create_implementation_plan(self) -> dict[str, Any]:
        """创建优化实施计划.

        Returns:
            实施计划
        """
        # 定义优化任务
        phases = [
            {
                "phase": "Phase 1: 快速优化",
                "duration": "1-2周",
                "tasks": [
                    {
                        "title": "Git操作批量化",
                        "priority": "HIGH",
                        "effort": "1-2天",
                        "expected_improvement": "30-40%",
                    },
                    {
                        "title": "添加分析进度提示",
                        "priority": "LOW",
                        "effort": "1-2天",
                        "expected_improvement": "用户体验",
                    },
                ],
                "total_expected_improvement": "30-40%",
            },
            {
                "phase": "Phase 2: 缓存优化",
                "duration": "2-3周",
                "tasks": [
                    {
                        "title": "实现项目扫描缓存机制",
                        "priority": "HIGH",
                        "effort": "3-5天",
                        "expected_improvement": "50-70%",
                    },
                    {
                        "title": "实现多级缓存策略",
                        "priority": "HIGH",
                        "effort": "5-7天",
                        "expected_improvement": "60-80%",
                    },
                ],
                "total_expected_improvement": "70-85% (累计)",
            },
            {
                "phase": "Phase 3: 算法和并发优化",
                "duration": "3-4周",
                "tasks": [
                    {
                        "title": "优化方法调用查找算法",
                        "priority": "MEDIUM",
                        "effort": "2-3天",
                        "expected_improvement": "20-30%",
                    },
                    {
                        "title": "实现并行文件分析",
                        "priority": "MEDIUM",
                        "effort": "7-10天",
                        "expected_improvement": "40-60%",
                    },
                    {
                        "title": "优化内存使用",
                        "priority": "MEDIUM",
                        "effort": "3-5天",
                        "expected_improvement": "内存减少50-70%",
                    },
                ],
                "total_expected_improvement": "85-95% (累计)",
            },
        ]

        return {
            "total_duration": "6-9周",
            "phases": phases,
            "expected_final_improvement": "85-95%",
            "risk_assessment": {
                "high_risk_tasks": [
                    "实现并行文件分析（复杂性高）",
                ],
                "mitigation": [
                    "分阶段实施，每阶段完成后进行性能测试",
                    "保持回滚能力",
                    "定期进行回归测试",
                ],
            },
        }


def generate_full_report(benchmark_data: list[dict[str, Any]], output_path: Path) -> Path:
    """生成完整性能报告.

    Args:
        benchmark_data: 基准测试数据
        output_path: 输出路径

    Returns:
        生成的报告路径
    """
    generator = PerformanceReportGenerator(benchmark_data)
    report = generator.generate_report()

    # 生成JSON报告
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

    # 生成Markdown报告
    md_path = output_path.with_suffix(".md")
    generate_markdown_report(report, md_path)

    return md_path


def generate_markdown_report(report: PerformanceReport, output_path: Path) -> None:
    """生成Markdown格式的报告.

    Args:
        report: 性能报告
        output_path: 输出路径
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# JCIA性能测试报告\n\n")
        f.write(f"**生成时间**: {datetime.now().isoformat()}\n\n")

        # 执行摘要
        summary = report.executive_summary
        f.write("## 1. 执行摘要\n\n")
        f.write(f"**当前状态**: {summary.get('status', 'N/A')}\n\n")
        f.write(f"**是否满足10分钟要求**: {'是' if summary.get('meets_10min_requirement') else '否'}\n\n")
        f.write(f"**总测试数**: {summary.get('total_tests', 0)}\n\n")
        f.write(f"**成功**: {summary.get('successful_tests', 0)}\n\n")
        f.write(f"**平均持续时间**: {summary.get('avg_duration_ms', 0):.2f} ms\n\n")
        f.write(f"**建议**: {summary.get('recommendation', 'N/A')}\n\n")

        # 基准测试结果
        f.write("## 2. 基准测试结果\n\n")
        for result in report.benchmark_results:
            f.write(f"### {result['operation']}\n\n")
            f.write(f"- **状态**: {result['status']}\n")
            f.write(f"- **持续时间**: {result['duration_ms']:.2f} ms\n")
            f.write(f"- **CPU时间**: {result.get('cpu_time_ms', 0):.2f} ms\n")
            f.write(f"- **处理文件数**: {result.get('files_processed', 0)}\n")
            f.write(f"- **处理速度**: {result.get('processing_speed', 0):.2f} files/sec\n\n")

        # 性能瓶颈
        f.write("## 3. 性能瓶颈分析\n\n")
        for i, bottleneck in enumerate(report.bottlenecks, 1):
            f.write(f"### 3.{i} {bottleneck['component']}\n\n")
            f.write(f"- **严重程度**: {bottleneck['severity']}\n")
            f.write(f"- **持续时间**: {bottleneck['duration_ms']:.2f} ms\n")
            f.write(f"- **描述**: {bottleneck['description']}\n")
            f.write(f"- **根本原因**: {bottleneck['root_cause']}\n\n")

        # 优化建议
        f.write("## 4. 优化方案\n\n")
        for i, rec in enumerate(report.optimization_recommendations, 1):
            f.write(f"### 4.{i} {rec['title']}\n\n")
            f.write(f"- **类别**: {rec['category']}\n")
            f.write(f"- **优先级**: {rec['priority']}\n")
            f.write(f"- **描述**: {rec['description']}\n")
            f.write(f"- **预期改进**: {rec['expected_improvement']}\n")
            f.write(f"- **实现复杂度**: {rec['implementation_complexity']}\n")
            f.write(f"- **预计工作量**: {rec['estimated_effort']}\n\n")

        # 实施计划
        plan = report.implementation_plan
        f.write("## 5. 优化实施计划\n\n")
        f.write(f"**总预计时长**: {plan.get('total_duration', 'N/A')}\n\n")
        f.write(f"**预期最终改进**: {plan.get('expected_final_improvement', 'N/A')}\n\n")

        for phase in plan.get('phases', []):
            f.write(f"### {phase['phase']} ({phase['duration']})\n\n")
            f.write(f"**预期改进**: {phase['total_expected_improvement']}\n\n")
            f.write("**任务列表**:\n\n")

            for task in phase['tasks']:
                f.write(f"- **{task['title']}**\n")
                f.write(f"  - 优先级: {task['priority']}\n")
                f.write(f"  - 工作量: {task['effort']}\n")
                f.write(f"  - 预期改进: {task['expected_improvement']}\n\n")

        # 风险评估
        risk = plan.get('risk_assessment', {})
        f.write("### 风险评估\n\n")
        f.write("**高风险任务**:\n")
        for task in risk.get('high_risk_tasks', []):
            f.write(f"- {task}\n")
        f.write("\n**缓解措施**:\n")
        for measure in risk.get('mitigation', []):
            f.write(f"- {measure}\n")

        f.write("\n---\n\n")
        f.write("*报告生成时间: " + datetime.now().isoformat() + "*\n")


def main() -> int:
    """主函数."""
    import argparse

    parser = argparse.ArgumentParser(description="生成性能测试报告")
    parser.add_argument(
        "--benchmark-data",
        type=Path,
        required=True,
        help="基准测试数据JSON文件",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("performance_report"),
        help="输出文件路径（不含扩展名）",
    )

    args = parser.parse_args()

    # 读取基准测试数据
    with open(args.benchmark_data, encoding="utf-8") as f:
        benchmark_data = json.load(f)

    # 生成报告
    generator = PerformanceReportGenerator(benchmark_data)
    generator.generate_report()  # noqa: F841

    # 保存报告
    report_path = generate_full_report(benchmark_data, args.output)
    print(f"报告已生成: {report_path}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
