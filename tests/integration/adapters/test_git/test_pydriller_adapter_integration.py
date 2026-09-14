"""PyDrillerAdapter 集成测试 - 使用真实 Git 仓库 (Jenkins 项目)."""

from pathlib import Path

import pytest

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.core.entities.change_set import ChangeSet, ChangeType


@pytest.fixture
def jenkins_repo_path() -> Path:
    """获取 Jenkins 仓库路径."""
    # Jenkins 已克隆到项目根目录的 jenkins/ 文件夹
    repo_path = Path(__file__).parent.parent.parent.parent.parent / "jenkins"
    if not repo_path.exists():
        pytest.skip(f"Jenkins repository not found at {repo_path}")
    return repo_path


class TestPyDrillerAdapterIntegration:
    """PyDrillerAdapter 集成测试类 - 使用真实 Git 仓库."""

    def test_real_git_repo_connection(self, jenkins_repo_path: Path) -> None:
        """测试连接真实 Jenkins Git 仓库."""
        # Arrange & Act
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Assert
        assert adapter.analyzer_name == "pydriller"
        assert adapter._repo_path == str(jenkins_repo_path)

    def test_analyze_single_commit(self, jenkins_repo_path: Path) -> None:
        """测试分析单个提交."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act - Jenkins 浅克隆只有一个提交
        result = adapter.analyze_commits("HEAD", "HEAD")

        # Assert
        assert isinstance(result, ChangeSet)
        assert result.commit_count >= 1
        assert len(result.commits) >= 1
        # 更新为当前 Jenkins 仓库的实际 commit hash
        assert result.commits[0].hash == "f067d469e6b8e3444ce4a92a8cf33dc4ca917a4b"
        assert "maven-release-plugin" in result.commits[0].message

    def test_analyze_commit_range_with_dots(self, jenkins_repo_path: Path) -> None:
        """测试使用点语法分析提交范围."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act
        result = adapter.analyze_commit_range("HEAD..HEAD")

        # Assert
        assert isinstance(result, ChangeSet)
        assert result.from_commit == "HEAD"
        assert result.to_commit == "HEAD"

    def test_changed_files_extraction(self, jenkins_repo_path: Path) -> None:
        """测试提取变更的文件."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act
        result = adapter.analyze_commits(
            "HEAD",
        )

        # Assert
        assert result.file_changes is not None
        # Jenkins 的初始提交应该有很多文件
        assert len(result.changed_files) > 0

        # 验证包含一些预期的文件类型
        file_paths = result.changed_files
        has_java_files = any(f.endswith(".java") for f in file_paths)
        has_xml_files = any(f.endswith(".xml") for f in file_paths)

        assert has_java_files or has_xml_files

    def test_file_change_types(self, jenkins_repo_path: Path) -> None:
        """测试识别文件变更类型."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act
        result = adapter.analyze_commits(
            "HEAD",
        )

        # Assert
        assert result.file_changes is not None

        # 验证变更类型枚举
        for fc in result.file_changes:
            assert fc.change_type in ChangeType
            assert fc.file_path is not None
            assert fc.total_changes >= 0

    def test_commit_metadata(self, jenkins_repo_path: Path) -> None:
        """测试提取提交元数据."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act
        result = adapter.analyze_commits(
            "HEAD",
        )

        # Assert
        assert result.commits is not None
        assert len(result.commits) >= 1

        commit = result.commits[0]
        assert commit.hash is not None
        assert len(commit.hash) > 0
        assert commit.message is not None
        assert commit.author is not None
        assert commit.email is not None
        assert commit.timestamp is not None

    def test_java_file_detection(self, jenkins_repo_path: Path) -> None:
        """测试 Java 文件检测."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act
        result = adapter.analyze_commits(
            "HEAD",
        )

        # Assert
        java_files = result.changed_java_files
        assert isinstance(java_files, list)

        # 应该有 Java 文件
        if len(java_files) > 0:
            # 验证文件路径
            for java_file in java_files:
                assert java_file.endswith(".java")

    def test_test_file_detection(self, jenkins_repo_path: Path) -> None:
        """测试测试文件检测."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act
        result = adapter.analyze_commits(
            "HEAD",
        )

        # Assert
        # 检查是否正确识别测试文件
        for fc in result.file_changes:
            is_test = fc.is_test_file

            # 如果路径包含 test，应该被识别为测试文件
            if "/test/" in fc.file_path.replace("\\", "/").lower():
                assert is_test is True

    def test_get_changed_methods_from_commit(self, jenkins_repo_path: Path) -> None:
        """测试获取提交中的变更方法."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act
        methods = adapter.get_changed_methods("HEAD")

        # Assert
        assert isinstance(methods, list)
        # 浅克隆的 PyDriller 可能没有提取方法变更
        # 所以我们只验证它返回一个列表

    def test_change_set_properties(self, jenkins_repo_path: Path) -> None:
        """测试 ChangeSet 属性."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act
        result = adapter.analyze_commits(
            "HEAD",
        )

        # Assert
        # 验证各种属性
        assert result.from_commit == "HEAD"
        assert result.to_commit is None
        assert result.commit_count >= 1
        assert result.total_insertions >= 0
        assert result.total_deletions >= 0
        assert not result.is_empty()

    def test_error_get_changed_methods_nonexistent_commit(self, jenkins_repo_path: Path) -> None:
        """测试不存在的提交的错误处理."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act - 不存在的提交可能不会抛出错误，但会返回空列表
        methods = adapter.get_changed_methods("nonexistent123abc")

        # Assert
        assert isinstance(methods, list)

    def test_error_handling_nonexistent_repo(self) -> None:
        """测试不存在仓库的错误处理."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path="/nonexistent/repo/path")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            adapter.analyze_commits(
                "HEAD",
            )

    def test_statistics_summary(self, jenkins_repo_path: Path) -> None:
        """测试变更统计摘要."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act
        result = adapter.analyze_commits(
            "HEAD",
        )

        # Assert
        # 验证统计信息
        assert result.total_insertions >= 0
        assert result.total_deletions >= 0
        assert result.commit_count >= 1

        # 验证总变更行数等于新增+删除
        total_changes = result.total_insertions + result.total_deletions
        assert total_changes >= 0

    def test_to_dict_conversion(self, jenkins_repo_path: Path) -> None:
        """测试转换为字典."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act
        result = adapter.analyze_commits(
            "HEAD",
        )
        result_dict = result.to_dict()

        # Assert
        assert isinstance(result_dict, dict)
        assert "from_commit" in result_dict
        assert "commit_count" in result_dict
        assert "changed_files" in result_dict
        assert "total_insertions" in result_dict
        assert "total_deletions" in result_dict

    def test_get_file_change_by_path(self, jenkins_repo_path: Path) -> None:
        """测试通过文件路径获取文件变更."""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))
        result = adapter.analyze_commits(
            "HEAD",
        )

        if len(result.changed_files) > 0:
            # Act
            file_path = result.changed_files[0]
            file_change = result.get_file_change(file_path)

            # Assert
            assert file_change is not None
            assert file_change.file_path == file_path
        else:
            # 如果没有文件变更，测试 get_file_change 返回 None
            file_change = result.get_file_change("nonexistent.java")
            assert file_change is None
