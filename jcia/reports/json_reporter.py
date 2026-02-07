"""JSON报告生成器.

生成JSON格式的测试报告。
"""

import json
from pathlib import Path

from jcia.reports.base import BaseReporter, ReportData, ReportResult


class JSONReporter(BaseReporter):
    """JSON报告生成器.

    生成JSON格式的测试报告，适合程序解析和CI/CD集成。
    """

    def __init__(self, output_dir: Path | None = None, indent: int = 2) -> None:
        """初始化JSON报告生成器.

        Args:
            output_dir: 输出目录
            indent: JSON缩进空格数
        """
        super().__init__(output_dir)
        self._indent = indent

    def get_format(self) -> str:
        """获取报告格式.

        Returns:
            str: 报告格式标识
        """
        return "json"

    def generate(self, data: ReportData) -> ReportResult:
        """生成JSON报告.

        Args:
            data: 报告数据

        Returns:
            ReportResult: 报告生成结果
        """
        try:
            self._ensure_output_dir()

            # 转换为字典
            report_dict = data.to_dict()

            # 生成JSON内容
            content = json.dumps(
                report_dict,
                indent=self._indent,
                ensure_ascii=False,
                default=str,
            )

            # 保存文件
            filename = self._get_output_filename("json")
            output_path = self._output_dir / filename
            output_path.write_text(content, encoding="utf-8")

            return ReportResult(
                success=True,
                output_path=output_path,
                content=content,
                format=self.get_format(),
                size_bytes=len(content.encode("utf-8")),
            )

        except Exception as e:
            return ReportResult(
                success=False,
                format=self.get_format(),
                error_message=str(e),
            )

    def generate_to_string(self, data: ReportData) -> str:
        """生成JSON字符串（不保存文件）.

        Args:
            data: 报告数据

        Returns:
            str: JSON字符串
        """
        report_dict = data.to_dict()
        return json.dumps(
            report_dict,
            indent=self._indent,
            ensure_ascii=False,
            default=str,
        )
