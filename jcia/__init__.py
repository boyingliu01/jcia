"""JCIA - Java Code Impact Analyzer.

代码变更影响分析工具，支持Maven项目的一键式代码变更影响分析、测试生成与回归验证。
"""

__version__ = "0.1.0"
__author__ = "JCIA Team"
__email__ = "jcia@example.com"

from jcia.core.entities.change_set import ChangeSet
from jcia.core.entities.impact_graph import ImpactGraph
from jcia.core.entities.test_case import TestCase

__all__ = ["ChangeSet", "ImpactGraph", "TestCase"]
