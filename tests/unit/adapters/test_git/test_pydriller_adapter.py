"""PyDrillerAdapter 单元测试."""

from enum import Enum
from unittest.mock import MagicMock, patch

import pytest

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.core.entities.change_set import ChangeSet, ChangeType


class DummyChangeType(Enum):
    RENAME = "rename"


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

    @patch("jcia.adapters.git.pydriller_adapter.Path.exists", return_value=True)
    @patch("jcia.adapters.git.pydriller_adapter.Repository")
    def test_analyze_commit_range_with_dots_syntax(self, mock_repo_class, mock_exists) -> None:
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
        mock_exists.assert_called()

    @patch("jcia.adapters.git.pydriller_adapter.Path.exists", return_value=True)
    @patch("jcia.adapters.git.pydriller_adapter.Repository")
    def test_analyze_commit_range_single_commit(self, mock_repo_class, mock_exists) -> None:
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
        mock_exists.assert_called()

    @patch("jcia.adapters.git.pydriller_adapter.Path.exists", return_value=True)
    @patch("jcia.adapters.git.pydriller_adapter.Repository")
    def test_analyze_commits_maps_commit_and_files(self, mock_repo_class, mock_exists) -> None:
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
        mock_exists.assert_called()

    def test_convert_file_change_supports_enum_and_unknown(self) -> None:
        """支持枚举 change_type 并对未知类型回退为 MODIFY."""
        adapter = PyDrillerAdapter(repo_path="/fake/repo")

        file_with_enum = MagicMock()
        file_with_enum.change_type = DummyChangeType.RENAME
        file_with_enum.filename = "Service.java"
        file_with_enum.added_lines = 1
        file_with_enum.deleted_lines = 2

        file_unknown = MagicMock()
        file_unknown.change_type = "WEIRD"
        file_unknown.filename = "Other.java"
        file_unknown.added_lines = 0
        file_unknown.deleted_lines = 0

        result_enum = adapter._convert_file_change(file_with_enum)
        result_unknown = adapter._convert_file_change(file_unknown)

        assert result_enum.change_type == ChangeType.RENAME
        assert result_unknown.change_type == ChangeType.MODIFY

    def test_convert_method_change_with_signature(self) -> None:
        """测试带签名的方法变更转换."""
        adapter = PyDrillerAdapter(repo_path="/fake/repo")
        mock_method = MagicMock()
        mock_method.long_name = "com.demo.Service.process(String, int)"
        mock_method.name = "process"
        mock_method.start_line = 10
        mock_method.end_line = 20

        result = adapter._convert_method_change(mock_method)

        assert result.class_name == "com.demo.Service"
        assert result.method_name == "process"
        assert result.signature == "(String, int)"
        assert result.line_start == 10
        assert result.line_end == 20

    def test_convert_method_change_without_signature(self) -> None:
        """测试不带签名的方法变更转换."""
        adapter = PyDrillerAdapter(repo_path="/fake/repo")
        mock_method = MagicMock()
        mock_method.long_name = "com.demo.Service.doWork"
        mock_method.name = "doWork"
        mock_method.start_line = 30
        mock_method.end_line = 40

        result = adapter._convert_method_change(mock_method)

        assert result.class_name == "com.demo.Service"
        assert result.method_name == "doWork"
        assert result.signature is None

    def test_convert_file_change_with_java_methods(self) -> None:
        """测试转换包含 Java 方法的 FileChange。"""
        adapter = PyDrillerAdapter(repo_path="/fake/repo")
        mock_file = MagicMock()
        mock_file.filename = "Service.java"
        mock_file.change_type = "MODIFY"
        mock_file.added_lines = 5
        mock_file.deleted_lines = 1

        mock_method = MagicMock()
        mock_method.long_name = "com.demo.Service.save()"
        mock_method.name = "save"
        mock_method.start_line = 5
        mock_method.end_line = 10
        mock_file.changed_methods = [mock_method]

        result = adapter._convert_file_change(mock_file)

        assert result.file_path == "Service.java"
        assert len(result.method_changes) == 1
        assert result.method_changes[0].method_name == "save"

    @patch("jcia.adapters.git.pydriller_adapter.Path.exists", return_value=True)
    @patch("jcia.adapters.git.pydriller_adapter.Repository")
    def test_get_changed_methods_returns_long_names(self, mock_repo_class, mock_exists) -> None:
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
        mock_exists.assert_called()

    @patch("jcia.adapters.git.pydriller_adapter.Path.exists", return_value=True)
    @patch("jcia.adapters.git.pydriller_adapter.Repository")
    def test_get_changed_methods_skips_missing_attribute(
        self, mock_repo_class, mock_exists
    ) -> None:
        """缺少 changed_methods 时返回空列表."""
        adapter = PyDrillerAdapter(repo_path="/fake/repo")
        mock_repo_instance = MagicMock()
        mock_repo_instance.traverse_commits.return_value = [object()]
        mock_repo_class.return_value = mock_repo_instance

        methods = adapter.get_changed_methods("abc123")

        assert methods == []
        mock_repo_class.assert_called_once()
        mock_exists.assert_called()

    @patch("jcia.adapters.git.pydriller_adapter.Repository")
    @patch("jcia.adapters.git.pydriller_adapter.Path.exists", return_value=False)
    def test_analyze_commits_raises_for_missing_repo(self, mock_exists, mock_repo_class) -> None:
        """仓库路径不存在时抛出 FileNotFoundError."""
        adapter = PyDrillerAdapter(repo_path="/missing/repo")

        with pytest.raises(FileNotFoundError):
            adapter.analyze_commits("abc123", "def456")

        mock_repo_class.assert_not_called()
        mock_exists.assert_called()
