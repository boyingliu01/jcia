"""报告生成器基类.

定义报告生成器的抽象接口和通用数据结构。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jcia.core.entities.change_set import ChangeSet
    from jcia.core.entities.impact_graph import ImpactGraph
    from jcia.core.entities.test_run import TestComparison, TestRun


@dataclass
class ReportData:
    """报告数据容器.

    Attributes:
        title: 报告标题
        timestamp: 生成时间戳
        test_run: 测试运行结果
        baseline_run: 基线测试运行
        comparison: 测试对比结果
        impact_graph: 影响图
        change_set: 变更集合
        metadata: 额外元数据
    """

    title: str = "测试报告"
    timestamp: datetime = field(default_factory=datetime.now)
    test_run: "TestRun | None" = None
    baseline_run: "TestRun | None" = None
    comparison: "TestComparison | None" = None
    impact_graph: "ImpactGraph | None" = None
    change_set: "ChangeSet | None" = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            dict[str, Any]: 报告数据字典
        """
        result: dict[str, Any] = {
            "title": self.title,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

        if self.test_run:
            result["test_run"] = self.test_run.to_dict()

        if self.baseline_run:
            result["baseline_run"] = self.baseline_run.to_dict()

        if self.comparison:
            result["comparison"] = self.comparison.to_dict()

        if self.impact_graph:
            result["impact_graph"] = self.impact_graph.to_dict()

        if self.change_set:
            result["change_set"] = self.change_set.to_dict()

        return result


@dataclass
class ReportResult:
    """报告生成结果.

    Attributes:
        success: 是否成功
        output_path: 输出文件路径
        content: 报告内容
        format: 报告格式
        size_bytes: 文件大小（字节）
        error_message: 错误信息
    """

    success: bool = True
    output_path: Path | None = None
    content: str = ""
    format: str = "unknown"
    size_bytes: int = 0
    error_message: str | None = None


class BaseReporter(ABC):
    """报告生成器基类.

    定义报告生成器的抽象接口。
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        """初始化报告生成器.

        Args:
            output_dir: 输出目录
        """
        self._output_dir = output_dir or Path.cwd()

    @property
    def output_dir(self) -> Path:
        """获取输出目录."""
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value: Path) -> None:
        """设置输出目录."""
        self._output_dir = value

    @abstractmethod
    def generate(self, data: ReportData) -> ReportResult:
        """生成报告.

        Args:
            data: 报告数据

        Returns:
            ReportResult: 报告生成结果
        """

    @abstractmethod
    def get_format(self) -> str:
        """获取报告格式.

        Returns:
            str: 报告格式标识
        """

    def _get_output_filename(self, extension: str) -> str:
        """生成输出文件名.

        Args:
            extension: 文件扩展名

        Returns:
            str: 文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"test_report_{timestamp}.{extension}"

    def _ensure_output_dir(self) -> None:
        """确保输出目录存在."""
        if not self._output_dir.exists():
            self._output_dir.mkdir(parents=True)

    def _format_percentage(self, value: float) -> str:
        """格式化百分比.

        Args:
            value: 百分比值（0-100）

        Returns:
            str: 格式化后的百分比字符串
        """
        return f"{value:.2f}%"

    def _format_success_rate(self, rate: float) -> str:
        """格式化成功率.

        Args:
            rate: 成功率（0-1）

        Returns:
            str: 格式化后的成功率字符串
        """
        return f"{rate * 100:.2f}%"
