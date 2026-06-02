"""领域实体定义.

本模块包含所有核心业务领域实体，采用不可变数据类实现。
"""

from jcia.core.entities.change_set import (
    ChangeSet,
    ChangeStatus,
    ChangeType,
    CommitInfo,
    FileChange,
    MethodChange,
)
from jcia.core.entities.impact_graph import (
    ImpactEdge,
    ImpactGraph,
    ImpactNode,
    ImpactSeverity,
    ImpactType,
)
from jcia.core.entities.remote_call import (
    RemoteCallChain,
    RemoteCallInfo,
    RemoteCallType,
    RemoteEndpoint,
)
from jcia.core.entities.test_case import (
    TestCase,
    TestPriority,
    TestSuite,
    TestType,
)
from jcia.core.entities.test_run import (
    CoverageData,
    RunStatus,
    RunType,
    TestComparison,
    TestDiff,
    TestResult,
    TestRun,
    TestStatus,
)

__all__ = [
    # 变更集合
    "ChangeSet",
    "ChangeStatus",
    "ChangeType",
    "CommitInfo",
    # 测试运行
    "CoverageData",
    "FileChange",
    # 影响图
    "ImpactEdge",
    "ImpactGraph",
    "ImpactNode",
    "ImpactSeverity",
    "ImpactType",
    "MethodChange",
    # 远程调用
    "RemoteCallChain",
    "RemoteCallInfo",
    "RemoteCallType",
    "RemoteEndpoint",
    "RunStatus",
    "RunType",
    # 测试用例
    "TestCase",
    "TestComparison",
    "TestDiff",
    "TestPriority",
    "TestResult",
    "TestRun",
    "TestStatus",
    "TestSuite",
    "TestType",
]
