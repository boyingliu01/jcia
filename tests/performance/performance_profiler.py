"""JCIA项目性能分析器.

提供全面的性能分析功能，包括：
- cProfile函数级性能分析
- 行级性能分析(line_profiler)
- 内存分析(memory_profiler)
- 性能基准测试
"""

import cProfile
import io
import json
import logging
import pstats
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class PerformanceMetrics:
    """性能指标数据类."""

    operation_name: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    duration_ms: float = 0.0
    cpu_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    call_count: int = 0
    error_count: int = 0

    # 详细性能数据
    profile_stats: dict[str, Any] = field(default_factory=dict)
    function_timings: list[dict[str, Any]] = field(default_factory=list)

    def finalize(self) -> None:
        """完成性能数据收集."""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "cpu_time_ms": self.cpu_time_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "call_count": self.call_count,
            "error_count": self.error_count,
            "profile_stats": self.profile_stats,
            "function_timings": self.function_timings,
        }


class PerformanceProfiler:
    """性能分析器主类.

    提供全面的性能分析功能。
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        """初始化性能分析器.

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or Path("performance_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_history: list[PerformanceMetrics] = []

    def profile_function(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> tuple[T, PerformanceMetrics]:
        """分析函数性能.

        Args:
            func: 要分析的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            tuple[返回值, 性能指标]
        """
        metrics = PerformanceMetrics(operation_name=func.__name__)

        # 启动内存跟踪
        tracemalloc.start()

        # 创建性能分析器
        profiler = cProfile.Profile()

        try:
            # 执行函数并分析
            start_cpu = time.process_time()
            profiler.enable()

            result = func(*args, **kwargs)

            profiler.disable()
            end_cpu = time.process_time()

            # 收集内存统计
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # 收集性能统计
            stats = pstats.Stats(profiler, stream=io.StringIO())
            stats.strip_dirs()
            stats.sort_stats(pstats.SortKey.CUMULATIVE)

            # 填充性能指标
            metrics.cpu_time_ms = (end_cpu - start_cpu) * 1000
            metrics.peak_memory_mb = peak / (1024 * 1024)
            metrics.call_count = 1

            # 提取函数级性能数据
            metrics.function_timings = self._extract_function_timings(stats)
            metrics.profile_stats = {
                "total_calls": stats.total_calls,
                "primitive_calls": stats.primitive_calls,
            }

        except Exception as e:
            metrics.error_count += 1
            logger.error(f"Error profiling function {func.__name__}: {e}")
            raise
        finally:
            metrics.finalize()
            self.metrics_history.append(metrics)

        return result, metrics

    def _extract_function_timings(self, stats: pstats.Stats) -> list[dict[str, Any]]:
        """提取函数级性能数据.

        Args:
            stats: 性能统计对象

        Returns:
            函数性能数据列表
        """
        timings = []
        # 限制只获取前20个最耗时的函数
        for func, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:20]:
            filename, line_no, func_name = func
            timings.append({
                "function": func_name,
                "file": filename,
                "line": line_no,
                "call_count": cc,
                "total_time_ms": ct * 1000,
                "own_time_ms": tt * 1000,
            })
        # 按总耗时排序
        timings.sort(key=lambda x: x["total_time_ms"], reverse=True)
        return timings

    def generate_report(self, report_path: Path | None = None) -> Path:
        """生成性能分析报告.

        Args:
            report_path: 报告文件路径

        Returns:
            报告文件路径
        """
        if report_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.output_dir / f"performance_report_{timestamp}.json"

        report_data = {
            "generated_at": datetime.now().isoformat(),
            "total_operations": len(self.metrics_history),
            "operations": [m.to_dict() for m in self.metrics_history],
            "summary": self._generate_summary(),
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Performance report generated: {report_path}")
        return report_path

    def _generate_summary(self) -> dict[str, Any]:
        """生成性能摘要.

        Returns:
            性能摘要数据
        """
        if not self.metrics_history:
            return {}

        durations = [m.duration_ms for m in self.metrics_history]
        cpu_times = [m.cpu_time_ms for m in self.metrics_history]
        memory_usage = [m.peak_memory_mb for m in self.metrics_history]

        return {
            "total_duration_ms": sum(durations),
            "avg_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "avg_cpu_time_ms": sum(cpu_times) / len(cpu_times) if cpu_times else 0,
            "avg_memory_mb": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
            "total_errors": sum(m.error_count for m in self.metrics_history),
        }


def profile_decorator(profiler: PerformanceProfiler | None = None):
    """性能分析装饰器.

    Args:
        profiler: 性能分析器实例

    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., tuple[T, PerformanceMetrics]]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> tuple[T, PerformanceMetrics]:
            prof = profiler or PerformanceProfiler()
            return prof.profile_function(func, *args, **kwargs)
        return wrapper
    return decorator


# 便捷的上下文管理器
class ProfileBlock:
    """性能分析代码块上下文管理器."""

    def __init__(self, name: str, profiler: PerformanceProfiler | None = None):
        """初始化.

        Args:
            name: 代码块名称
            profiler: 性能分析器
        """
        self.name = name
        self.profiler = profiler or PerformanceProfiler()
        self.metrics: PerformanceMetrics | None = None

    def __enter__(self) -> "ProfileBlock":
        """进入上下文."""
        self.metrics = PerformanceMetrics(operation_name=self.name)
        tracemalloc.start()
        self._start_cpu = time.process_time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """退出上下文."""
        if self.metrics:
            end_cpu = time.process_time()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            self.metrics.cpu_time_ms = (end_cpu - self._start_cpu) * 1000
            self.metrics.peak_memory_mb = peak / (1024 * 1024)
            self.metrics.finalize()

            if exc_type is not None:
                self.metrics.error_count += 1

            self.profiler.metrics_history.append(self.metrics)
