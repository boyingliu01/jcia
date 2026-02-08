"""分析变更影响用例.

负责协调变更分析和影响分析的完整流程。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jcia.core.entities.change_set import ChangeSet
    from jcia.core.entities.impact_graph import ImpactGraph
    from jcia.core.interfaces.analyzer import ChangeAnalyzer
    from jcia.core.interfaces.call_chain_analyzer import CallChainAnalyzer


@dataclass
class AnalyzeImpactRequest:
    """分析影响请求.

    Attributes:
        repo_path: 仓库路径
        from_commit: 起始提交
        to_commit: 结束提交（可选）
        commit_range: 提交范围（替代from/to）
        max_depth: 最大追溯深度
        include_test_files: 是否包含测试文件
    """

    repo_path: Path
    from_commit: str | None = None
    to_commit: str | None = None
    commit_range: str | None = None
    max_depth: int = 10
    include_test_files: bool = False


@dataclass
class AnalyzeImpactResponse:
    """分析影响响应.

    Attributes:
        change_set: 变更集合
        impact_graph: 影响图
        summary: 影响摘要
    """

    change_set: "ChangeSet"
    impact_graph: "ImpactGraph"
    summary: dict = field(default_factory=dict)


class AnalyzeImpactUseCase:
    """分析变更影响用例.

    协调变更分析和影响分析，计算代码变更的完整影响范围。

    流程：
        1. 使用ChangeAnalyzer分析Git提交差异
        2. 使用ImpactAnalysisService分析影响范围
        3. 生成影响摘要
    """

    def __init__(
        self,
        change_analyzer: "ChangeAnalyzer",
        call_chain_analyzer: "CallChainAnalyzer | None" = None,
    ) -> None:
        """初始化用例.

        Args:
            change_analyzer: 变更分析器
            call_chain_analyzer: 调用链分析器（可选，某些实现可能同时实现两个接口）
        """
        self._analyzer = change_analyzer
        # 某些适配器可能同时实现两个接口
        self._call_chain_analyzer = call_chain_analyzer

    def execute(self, request: AnalyzeImpactRequest) -> AnalyzeImpactResponse:
        """执行分析影响用例.

        Args:
            request: 分析请求

        Returns:
            AnalyzeImpactResponse: 分析响应

        Raises:
            ValueError: 请求参数无效
            Exception: 分析过程中发生错误
        """
        # 验证请求
        self._validate_request(request)

        # 分析变更
        change_set = self._analyze_changes(request)

        # 如果没有变更，返回空结果
        if change_set.is_empty():
            return self._create_empty_response(change_set)

        # 分析影响
        impact_graph = self._analyze_impact(change_set, request.max_depth)

        # 生成摘要
        summary = self._generate_summary(change_set, impact_graph)

        return AnalyzeImpactResponse(
            change_set=change_set,
            impact_graph=impact_graph,
            summary=summary,
        )

    def _validate_request(self, request: AnalyzeImpactRequest) -> None:
        """验证请求参数.

        Args:
            request: 分析请求

        Raises:
            ValueError: 请求参数无效
        """
        if not request.repo_path.exists():
            msg = f"仓库路径不存在: {request.repo_path}"
            raise ValueError(msg)

        if request.commit_range is None:
            if request.from_commit is None:
                msg = "必须提供commit_range或from_commit"
                raise ValueError(msg)
        elif request.from_commit is not None or request.to_commit is not None:
            msg = "不能同时使用commit_range和from_commit/to_commit"
            raise ValueError(msg)

        if request.max_depth < 1:
            msg = "max_depth必须大于0"
            raise ValueError(msg)

    def _analyze_changes(self, request: AnalyzeImpactRequest) -> "ChangeSet":
        """分析变更.

        Args:
            request: 分析请求

        Returns:
            ChangeSet: 变更集合
        """
        # 获取变更集
        if request.commit_range:
            change_set = self._analyzer.analyze_commit_range(request.commit_range)
        else:
            change_set = self._analyzer.analyze_commits(
                request.from_commit or "",
                request.to_commit,
            )

        # 根据include_test_files参数过滤测试文件
        if not request.include_test_files:
            # 过滤掉测试文件，只保留非测试文件的变更
            change_set.file_changes = [fc for fc in change_set.file_changes if not fc.is_test_file]

        return change_set

    def _analyze_impact(self, change_set: "ChangeSet", max_depth: int) -> "ImpactGraph":
        """分析影响.

        Args:
            change_set: 变更集合
            max_depth: 最大追溯深度

        Returns:
            ImpactGraph: 影响图

        Raises:
            ValueError: 调用链分析器未配置
            Exception: 分析过程中发生错误
        """
        # 导入ImpactAnalysisService避免和循环依赖
        from jcia.core.interfaces.call_chain_analyzer import (  # noqa: TCH001
            CallChainAnalyzer,
        )
        from jcia.core.services.impact_analysis_service import ImpactAnalysisService

        # 使用提供的调用链分析器
        analyzer: CallChainAnalyzer
        if self._call_chain_analyzer is not None:
            analyzer = self._call_chain_analyzer
        else:
            msg = "调用链分析器未配置，无法进行影响分析"
            raise ValueError(msg)

        try:
            impact_service = ImpactAnalysisService(call_chain_analyzer=analyzer)
            return impact_service.analyze(change_set, max_depth=max_depth)
        except Exception as e:
            raise Exception(f"影响分析失败: {e}") from e

    def _generate_summary(self, change_set: "ChangeSet", impact_graph: "ImpactGraph") -> dict:
        """生成摘要.

        Args:
            change_set: 变更集合
            impact_graph: 影响图

        Returns:
            dict: 摘要信息
        """
        return {
            "commit_range": f"{change_set.from_commit}..{change_set.to_commit or 'HEAD'}",
            "commit_count": change_set.commit_count,
            "changed_files": len(change_set.changed_files),
            "changed_java_files": len(change_set.changed_java_files),
            "changed_methods": len(change_set.changed_methods),
            "total_affected_methods": impact_graph.total_affected_methods,
            "direct_impacts": impact_graph.direct_impact_count,
            "indirect_impacts": impact_graph.indirect_impact_count,
            "affected_classes": len(impact_graph.affected_classes),
            "high_severity_count": impact_graph.high_severity_count,
        }

    def _create_empty_response(self, change_set: "ChangeSet") -> AnalyzeImpactResponse:
        """创建空响应.

        Args:
            change_set: 空的变更集合

        Returns:
            AnalyzeImpactResponse: 空响应
        """
        from jcia.core.entities.impact_graph import ImpactGraph

        return AnalyzeImpactResponse(
            change_set=change_set,
            impact_graph=ImpactGraph(change_set_id=change_set.from_commit),
            summary={"status": "no_changes", "message": "没有检测到变更"},
        )
