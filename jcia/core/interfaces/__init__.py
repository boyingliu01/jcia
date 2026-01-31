"""核心抽象接口定义.

本模块定义了所有核心业务抽象接口，遵循依赖倒置原则(DIP)。
所有外部实现都通过这些接口与核心业务逻辑交互。
"""

from jcia.core.interfaces.ai_service import (
    AIAnalyzer,
    AIProvider,
    AITestGenerator,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    TestGenerationRequest,
    TestGenerationResponse,
)
from jcia.core.interfaces.analyzer import ChangeAnalyzer, ImpactAnalyzer
from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainAnalyzer,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)
from jcia.core.interfaces.repository import (
    ChangeImpactRepository,
    TestDiffRepository,
    TestResultRepository,
    TestRunRepository,
)
from jcia.core.interfaces.test_runner import (
    TestExecutionResult,
    TestExecutor,
    TestGenerator,
    TestSelectionStrategy,
    TestSelector,
    TestSuiteResult,
)
from jcia.core.interfaces.tool_wrapper import (
    JavaToolWrapper,
    MavenPluginWrapper,
    ToolResult,
    ToolStatus,
    ToolType,
    ToolWrapper,
)

__all__ = [
    # 分析器接口
    "ChangeAnalyzer",
    "ImpactAnalyzer",
    # 调用链分析器接口
    "AnalyzerType",
    "CallChainAnalyzer",
    "CallChainDirection",
    "CallChainGraph",
    "CallChainNode",
    # AI 服务接口
    "AIAnalyzer",
    "AIProvider",
    "AITestGenerator",
    "CodeAnalysisRequest",
    "CodeAnalysisResponse",
    "TestGenerationRequest",
    "TestGenerationResponse",
    # 仓储接口
    "ChangeImpactRepository",
    "TestDiffRepository",
    "TestResultRepository",
    "TestRunRepository",
    # 测试运行器接口
    "TestExecutionResult",
    "TestExecutor",
    "TestGenerator",
    "TestSelector",
    "TestSelectionStrategy",
    "TestSuiteResult",
    # 工具封装接口
    "JavaToolWrapper",
    "MavenPluginWrapper",
    "ToolResult",
    "ToolStatus",
    "ToolType",
    "ToolWrapper",
]
