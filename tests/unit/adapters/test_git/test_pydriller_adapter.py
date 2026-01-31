"""PyDrillerAdapter 单元测试."""

from unittest.mock import MagicMock, patch

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.core.entities.change_set import ChangeSet


class TestPyDrillerAdapter:
    """PyDrillerAdapter 测试类."""

    def test_analyzer_name_returns_pydriller(self) -> None:
        """测试分析器名称."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path="/fake/repo")

        # Act
        name = adapter.analyzer_name

        # Assert
        assert name == "pydriller"

    def test_init_stores_repo_path(self) -> None:
        """测试初始化存储仓库路径."""
        # Arrange & Act
        adapter = PyDrillerAdapter(repo_path="/test/repo")

        # Assert
        assert adapter._repo_path == "/test/repo"

    @patch("jcia.adapters.git.pydriller_adapter.Repository")
    def test_analyze_commit_range_with_dots_syntax(self, mock_repo_class) -> None:
        """测试分析提交范围语法."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path="/fake/repo")
        mock_repo_instance = MagicMock()
        mock_repo_instance.traverse_commits.return_value = []
        mock_repo_class.return_value = mock_repo_instance

        # Act
        result = adapter.analyze_commit_range("abc123..def456")

        # Assert
        assert isinstance(result, ChangeSet)
        mock_repo_class.assert_called_once()

    @patch("jcia.adapters.git.pydriller_adapter.Repository")
    def test_analyze_commit_range_single_commit(self, mock_repo_class) -> None:
        """测试单个提交范围."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path="/fake/repo")
        mock_repo_instance = MagicMock()
        mock_repo_instance.traverse_commits.return_value = []
        mock_repo_class.return_value = mock_repo_instance

        # Act
        result = adapter.analyze_commit_range("abc123")

        # Assert
        assert isinstance(result, ChangeSet)
        mock_repo_class.assert_called_once()
