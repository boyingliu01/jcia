"""报告生成模块.

提供多种格式的报告生成器，包括HTML、JSON、Markdown报告。
"""

from jcia.reports.base import BaseReporter, ReportData
from jcia.reports.html_reporter import HTMLReporter
from jcia.reports.json_reporter import JSONReporter
from jcia.reports.markdown_reporter import MarkdownReporter

__all__ = [
    "BaseReporter",
    "HTMLReporter",
    "JSONReporter",
    "MarkdownReporter",
    "ReportData",
]
