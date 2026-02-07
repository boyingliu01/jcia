"""测试分析变更影响用例."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from jcia.core.entities.change_set import ChangeSet, ChangeType, CommitInfo, FileChange
from jcia.core.entities.impact_graph import (
    ImpactGraph,
    ImpactNode,
    ImpactSeverity,
    ImpactType,
)
from jcia.core.use_cases.analyze_impact import (
    AnalyzeImpactRequest,
    AnalyzeImpactResponse,
    AnalyzeImpactUseCase,
)


@dataclass
class MockCallChain:
    """模拟调用链."""

    root: Mock | None = None


class TestAnalyzeImpactRequest:
    """测试AnalyzeImpactRequest."""

    def test_init_with_required_fields(self) -> None:
        """测试使用必需字段初始化."""
        request = AnalyzeImpactRequest(repo_path=Path("/test/repo"))
        assert request.repo_path == Path("/test/repo")
        assert request.from_commit is None
        assert request.to_commit is None
        assert request.commit_range is None
        assert request.max_depth == 10
        assert request.include_test_files is False

    def test_init_with_all_fields(self) -> None:
        """测试使用所有字段初始化."""
        request = AnalyzeImpactRequest(
            repo_path=Path("/test/repo"),
            from_commit="abc123",
            to_commit="def456",
            max_depth=5,
            include_test_files=True,
        )
        assert request.from_commit == "abc123"
        assert request.to_commit == "def456"
        assert request.max_depth == 5
        assert request.include_test_files is True

    def test_init_with_commit_range(self) -> None:
        """测试使用commit_range初始化."""
        request = AnalyzeImpactRequest(repo_path=Path("/test/repo"), commit_range="abc123..def456")
        assert request.commit_range == "abc123..def456"


class TestAnalyzeImpactResponse:
    """测试AnalyzeImpactResponse."""

    def test_init(self) -> None:
        """测试初始化."""
        change_set = Mock(spec=ChangeSet)
        impact_graph = Mock(spec=ImpactGraph)
        summary = {"key": "value"}

        response = AnalyzeImpactResponse(
            change_set=change_set, impact_graph=impact_graph, summary=summary
        )
        assert response.change_set is change_set
        assert response.impact_graph is impact_graph
        assert response.summary == summary


class TestAnalyzeImpactUseCase:
    """测试AnalyzeImpactUseCase."""

    @pytest.fixture
    def mock_analyzer(self) -> Mock:
        """创建模拟分析器."""
        analyzer = Mock()
        analyzer.analyzer_name = "mock"
        return analyzer

    @pytest.fixture
    def use_case(self, mock_analyzer: Mock) -> AnalyzeImpactUseCase:
        """创建用例实例."""
        return AnalyzeImpactUseCase(change_analyzer=mock_analyzer)

    @pytest.fixture
    def valid_repo_path(self, tmp_path: Path) -> Path:
        """创建有效的仓库路径."""
        return tmp_path

    def test_init_with_analyzer(self, use_case: AnalyzeImpactUseCase) -> None:
        """测试使用分析器初始化用例."""
        assert use_case._analyzer is not None

    def test_execute_with_commit_range(self, mock_analyzer: Mock, valid_repo_path: Path) -> None:
        """测试使用commit_range执行."""
        # Arrange
        request = AnalyzeImpactRequest(repo_path=valid_repo_path, commit_range="abc123..def456")

        # 设置模拟返回值
        mock_change_set = self._create_mock_change_set()
        mock_analyzer.analyze_commit_range.return_value = mock_change_set

        # 创建模拟调用链分析器
        mock_call_chain_analyzer = MagicMock()

        # 创建用例实例，带有调用链分析器
        use_case = AnalyzeImpactUseCase(
            change_analyzer=mock_analyzer,
            call_chain_analyzer=mock_call_chain_analyzer,
        )

        with patch(
            "jcia.core.services.impact_analysis_service.ImpactAnalysisService"
        ) as mock_service:
            mock_impact_graph = self._create_mock_impact_graph()
            mock_service.return_value.analyze.return_value = mock_impact_graph

            # Act
            response = use_case.execute(request)

            # Assert
            assert isinstance(response, AnalyzeImpactResponse)
            mock_analyzer.analyze_commit_range.assert_called_once_with("abc123..def456")

    def test_execute_with_from_to_commits(self, mock_analyzer: Mock, valid_repo_path: Path) -> None:
        """测试使用from/to提交执行."""
        # Arrange
        request = AnalyzeImpactRequest(
            repo_path=valid_repo_path, from_commit="abc123", to_commit="def456"
        )

        mock_change_set = self._create_mock_change_set()
        mock_analyzer.analyze_commits.return_value = mock_change_set

        # 创建模拟调用链分析器
        mock_call_chain_analyzer = MagicMock()

        # 创建用例实例，带有调用链分析器
        use_case = AnalyzeImpactUseCase(
            change_analyzer=mock_analyzer,
            call_chain_analyzer=mock_call_chain_analyzer,
        )

        with patch(
            "jcia.core.services.impact_analysis_service.ImpactAnalysisService"
        ) as mock_service:
            mock_impact_graph = self._create_mock_impact_graph()
            mock_service.return_value.analyze.return_value = mock_impact_graph

            # Act
            response = use_case.execute(request)

            # Assert
            assert isinstance(response, AnalyzeImpactResponse)
            mock_analyzer.analyze_commits.assert_called_once_with("abc123", "def456")

    def test_execute_with_empty_change_set(
        self, use_case: AnalyzeImpactUseCase, mock_analyzer: Mock, valid_repo_path: Path
    ) -> None:
        """测试使用空变更集执行."""
        # Arrange
        request = AnalyzeImpactRequest(repo_path=valid_repo_path, commit_range="abc123..def456")

        empty_change_set = ChangeSet(
            from_commit="abc123",
            to_commit="def456",
        )
        mock_analyzer.analyze_commit_range.return_value = empty_change_set

        # Act
        response = use_case.execute(request)

        # Assert
        assert isinstance(response, AnalyzeImpactResponse)
        assert response.change_set.is_empty
        assert response.impact_graph.total_affected_methods == 0
        assert response.summary["status"] == "no_changes"

    def test_validate_request_invalid_path(self, use_case: AnalyzeImpactUseCase) -> None:
        """测试验证请求：无效路径."""
        # Arrange
        request = AnalyzeImpactRequest(repo_path=Path("/nonexistent/path"))

        # Act & Assert
        with pytest.raises(ValueError, match="仓库路径不存在"):
            use_case.execute(request)

    def test_validate_request_missing_commit(
        self, use_case: AnalyzeImpactUseCase, valid_repo_path: Path
    ) -> None:
        """测试验证请求：缺少提交."""
        # Arrange
        request = AnalyzeImpactRequest(repo_path=valid_repo_path)

        # Act & Assert
        with pytest.raises(ValueError, match="必须提供"):
            use_case.execute(request)

    def test_validate_request_invalid_max_depth(
        self, use_case: AnalyzeImpactUseCase, valid_repo_path: Path
    ) -> None:
        """测试验证请求：无效max_depth."""
        # Arrange
        request = AnalyzeImpactRequest(repo_path=valid_repo_path, from_commit="abc123", max_depth=0)

        # Act & Assert
        with pytest.raises(ValueError, match="max_depth必须大于0"):
            use_case.execute(request)

    def test_validate_request_conflict_commit_parameters(
        self, use_case: AnalyzeImpactUseCase, valid_repo_path: Path
    ) -> None:
        """测试验证请求：冲突的提交参数."""
        # Arrange
        request = AnalyzeImpactRequest(
            repo_path=valid_repo_path,
            from_commit="abc123",
            commit_range="abc123..def456",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="不能同时使用"):
            use_case.execute(request)

    def test_generate_summary(self, mock_analyzer: Mock, valid_repo_path: Path) -> None:
        """测试生成摘要."""
        # Arrange
        request = AnalyzeImpactRequest(
            repo_path=valid_repo_path, from_commit="abc123", to_commit="def456"
        )

        # 创建模拟调用链分析器
        mock_call_chain_analyzer = MagicMock()

        # 创建用例实例，带有调用链分析器
        use_case = AnalyzeImpactUseCase(
            change_analyzer=mock_analyzer,
            call_chain_analyzer=mock_call_chain_analyzer,
        )

        mock_change_set = self._create_mock_change_set()
        mock_impact_graph = self._create_mock_impact_graph()

        # 直接调用_generate_summary测试
        summary = use_case._generate_summary(mock_change_set, mock_impact_graph)

        # Assert
        assert "commit_range" in summary
        assert "changed_files" in summary
        assert "total_affected_methods" in summary
        assert summary["commit_range"] == "abc123..def456"
        assert summary["changed_files"] == 1
        assert summary["total_affected_methods"] == 1

    def _create_mock_change_set(self) -> ChangeSet:
        """创建模拟变更集合."""
        file_change = FileChange(
            file_path="com/example/Test.java",
            change_type=ChangeType.MODIFY,
            insertions=10,
            deletions=5,
        )
        # Add method change to make it complete
        from jcia.core.entities.change_set import MethodChange

        file_change.method_changes.append(
            MethodChange(
                class_name="com.example.Test",
                method_name="testMethod",
                signature="()",
            )
        )

        change_set = ChangeSet(
            from_commit="abc123",
            to_commit="def456",
            commits=[
                CommitInfo(
                    hash="abc123",
                    author="Test Author",
                    email="test@example.com",
                    message="Test commit",
                    timestamp=datetime.now(),
                )
            ],
            file_changes=[file_change],
        )
        return change_set

    def _create_mock_impact_graph(self) -> ImpactGraph:
        """创建模拟影响图."""
        impact_graph = ImpactGraph(change_set_id="abc123")
        node = ImpactNode(
            method_name="com.example.Test.method()",
            class_name="com.example.Test",
            impact_type=ImpactType.DIRECT,
            severity=ImpactSeverity.HIGH,
            depth=0,
        )
        impact_graph.add_node(node)
        return impact_graph
