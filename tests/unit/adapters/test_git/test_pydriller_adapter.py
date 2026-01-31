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

    @patch("jcia.adapters.git.pydriller_adapter.Repository")
    def test_analyze_commits_maps_commit_and_files(self, mock_repo_class) -> None:
        """测试提交与文件变更映射."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path="/fake/repo")
        mock_repo_instance = MagicMock()
        mock_file = MagicMock()
        mock_file.change_type = "ADD"
        mock_file.filename = "src/Service.java"
        mock_file.added_lines = 10
        mock_file.deleted_lines = 2

        mock_author = MagicMock()
        mock_author.name = "alice"
        mock_author.email = "alice@example.com"

        mock_commit = MagicMock()
        mock_commit.hash = "abc123"
        mock_commit.msg = "Add service"
        mock_commit.author = mock_author
        mock_commit.author_date = MagicMock()
        mock_commit.parents = [MagicMock(hash="parent1")]
        mock_commit.modified_files = [mock_file]

        mock_repo_instance.traverse_commits.return_value = [mock_commit]
        mock_repo_class.return_value = mock_repo_instance

        # Act
        result = adapter.analyze_commits("abc123", "def456")

        # Assert
        assert result.commit_count == 1
        assert result.changed_files == ["src/Service.java"]
        assert result.total_insertions == 10
        assert result.total_deletions == 2
        assert result.commits[0].hash == "abc123"

    @patch("jcia.adapters.git.pydriller_adapter.Repository")
    def test_get_changed_methods_returns_long_names(self, mock_repo_class) -> None:
        """测试获取变更方法列表."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path="/fake/repo")
        mock_repo_instance = MagicMock()
        method_a = MagicMock(long_name="com.demo.Service.methodA()")
        method_b = MagicMock(long_name="com.demo.Service.methodB()")
        mock_commit = MagicMock(changed_methods=[method_a, method_b])

        mock_repo_instance.traverse_commits.return_value = [mock_commit]
        mock_repo_class.return_value = mock_repo_instance

        # Act
        methods = adapter.get_changed_methods("abc123")

        # Assert
        assert methods == [
            "com.demo.Service.methodA()",
            "com.demo.Service.methodB()",
        ]
        mock_repo_class.assert_called_once()
