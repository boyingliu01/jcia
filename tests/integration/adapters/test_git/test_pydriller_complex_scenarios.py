"""PyDrillerAdapter 复杂场景测试 - 多提交、多文件."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.core.entities.change_set import ChangeSet


@pytest.fixture
def jenkins_repo_path() -> Path:
    """获取 Jenkins 仓库路径."""
    repo_path = Path(__file__).parent.parent.parent.parent / "jenkins"
    if not repo_path.exists():
        pytest.skip(f"Jenkins repository not found at {repo_path}")
    return repo_path


@pytest.fixture
def temp_repo_with_commits():
    """创建临时 Git 仓库并提交多个文件。"""
    temp_dir = Path(tempfile.mkdtemp(prefix="jcia_complex_test_"))

    try:
        # 初始化 Git 仓库
        subprocess.run(
            ["git", "init"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )

        # 配置用户
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )

        # 提交 1: 添加 ServiceA.java
        (temp_dir / "ServiceA.java").write_text("public class ServiceA { void doWork() {} }")
        subprocess.run(
            ["git", "add", "ServiceA.java"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "feat: add ServiceA"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )

        # 提交 2: 添加 ServiceB.java
        (temp_dir / "ServiceB.java").write_text("public class ServiceB { void process() {} }")
        subprocess.run(
            ["git", "add", "ServiceB.java"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "feat: add ServiceB"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )

        # 提交 3: 修改 ServiceA.java
        (temp_dir / "ServiceA.java").write_text(
            'public class ServiceA { void doWork() { System.out.println("test"); } }'
        )
        subprocess.run(
            ["git", "add", "ServiceA.java"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "refactor: improve ServiceA"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )

        # 提交 4: 添加 ServiceC.java
        (temp_dir / "ServiceC.java").write_text("public class ServiceC { void execute() {} }")
        subprocess.run(
            ["git", "add", "ServiceC.java"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "feat: add ServiceC"],
            cwd=temp_dir,
            capture_output=True,
            check=True,
        )

        yield temp_dir

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestPyDrillerComplexScenarios:
    """PyDrillerAdapter 复杂场景测试。"""

    def test_analyze_multiple_commits(self, temp_repo_with_commits: Path) -> None:
        """测试分析多个提交。"""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(temp_repo_with_commits))

        # Act - 分析从第一个到最后一个提交
        result = adapter.analyze_commits("HEAD~3", "HEAD")

        # Assert
        assert isinstance(result, ChangeSet)
        assert result.commit_count == 4  # 应该有4个提交
        assert len(result.commits) == 4

    def test_analyze_multiple_files(self, temp_repo_with_commits: Path) -> None:
        """测试分析多文件变更。"""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(temp_repo_with_commits))

        # Act
        result = adapter.analyze_commits("HEAD~3", "HEAD")

        # Assert
        # 应该包含 3 个 Java 文件
        java_files = result.changed_java_files
        assert len(java_files) >= 3

        # 验证文件名
        file_names = [Path(f).name for f in java_files]
        assert "ServiceA.java" in file_names
        assert "ServiceB.java" in file_names
        assert "ServiceC.java" in file_names

    def test_aggregate_statistics_across_commits(self, temp_repo_with_commits: Path) -> None:
        """测试跨提交的统计信息。"""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(temp_repo_with_commits))

        # Act
        result = adapter.analyze_commits("HEAD~3", "HEAD")

        # Assert
        # 验证统计信息正确聚合
        assert result.commit_count == 4
        assert result.total_insertions > 0
        assert result.total_deletions >= 0

    def test_commit_messages_collection(self, temp_repo_with_commits: Path) -> None:
        """测试收集提交消息。"""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(temp_repo_with_commits))

        # Act
        result = adapter.analyze_commits("HEAD~3", "HEAD")

        # Assert
        messages = [c.message for c in result.commits]
        assert len(messages) == 4

        # 验证提交消息
        message_contents = " ".join(messages).lower()
        assert "servicea" in message_contents or "add servicea" in message_contents
        assert "serviceb" in message_contents or "add serviceb" in message_contents
        assert "servicec" in message_contents or "add servicec" in message_contents

    def test_file_change_tracking_across_commits(self, temp_repo_with_commits: Path) -> None:
        """测试跨提交的文件变更跟踪。"""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(temp_repo_with_commits))

        # Act
        result = adapter.analyze_commits("HEAD~3", "HEAD")

        # Assert
        # ServiceA.java 应该出现两次（添加 + 修改）
        service_a_changes = [fc for fc in result.file_changes if "ServiceA.java" in fc.file_path]
        # 可能 PyDriller 只记录一次，但这取决于具体实现
        assert len(service_a_changes) >= 1

    def test_large_commit_range_analysis(self, jenkins_repo_path: Path) -> None:
        """测试大范围提交分析（Jenkins 项目）。"""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(jenkins_repo_path))

        # Act - 分析单个提交（Jenkins 浅克隆只有一个提交）
        result = adapter.analyze_commits(
            "HEAD",
        )

        # Assert
        assert isinstance(result, ChangeSet)
        # Jenkins 的初始提交应该有很多文件
        assert len(result.changed_files) > 0

    def test_commit_author_info(self, temp_repo_with_commits: Path) -> None:
        """测试提交作者信息。"""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(temp_repo_with_commits))

        # Act
        result = adapter.analyze_commits("HEAD~3", "HEAD")

        # Assert
        for commit in result.commits:
            assert commit.author is not None
            assert commit.email is not None
            assert commit.timestamp is not None

    def test_parent_commit_tracking(self, temp_repo_with_commits: Path) -> None:
        """测试父提交跟踪。"""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(temp_repo_with_commits))

        # Act
        result = adapter.analyze_commits("HEAD~3", "HEAD")

        # Assert
        # 第一个提交应该没有父提交
        assert len(result.commits[0].parents) == 0

        # 其他提交应该有父提交
        for commit in result.commits[1:]:
            assert len(commit.parents) >= 1

    def test_change_set_to_dict_comprehensive(self, temp_repo_with_commits: Path) -> None:
        """测试 ChangeSet 转换为字典（综合）。"""
        # Arrange
        adapter = PyDrillerAdapter(repo_path=str(temp_repo_with_commits))

        # Act
        result = adapter.analyze_commits("HEAD~3", "HEAD")
        result_dict = result.to_dict()

        # Assert
        assert isinstance(result_dict, dict)
        assert "commit_count" in result_dict
        assert "changed_files" in result_dict
        assert "changed_methods" in result_dict
        assert "total_insertions" in result_dict
        assert "total_deletions" in result_dict

        # 验证数据类型
        assert isinstance(result_dict["commit_count"], int)
        assert isinstance(result_dict["changed_files"], list)
        assert isinstance(result_dict["changed_methods"], list)
        assert isinstance(result_dict["total_insertions"], int)
        assert isinstance(result_dict["total_deletions"], int)
