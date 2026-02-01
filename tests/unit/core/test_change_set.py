"""ChangeSet领域实体单元测试."""

from datetime import datetime

from jcia.core.entities.change_set import (
    ChangeSet,
    ChangeType,
    CommitInfo,
    FileChange,
    MethodChange,
)


class TestMethodChange:
    """MethodChange测试类."""

    def test_full_name_with_signature(self) -> None:
        """测试带签名的全限定名."""
        method = MethodChange(
            class_name="com.example.Service",
            method_name="doSomething",
            signature="(String, int)",
        )
        assert method.full_name == "com.example.Service.doSomething(String, int)"

    def test_full_name_without_signature(self) -> None:
        """测试不带签名的全限定名."""
        method = MethodChange(
            class_name="com.example.Service",
            method_name="doSomething",
        )
        assert method.full_name == "com.example.Service.doSomething"

    def test_is_new(self) -> None:
        """测试新增方法判断."""
        method = MethodChange(
            class_name="com.example.Service",
            method_name="newMethod",
            change_type=ChangeType.ADD,
        )
        assert method.is_new is True
        assert method.is_deleted is False

    def test_is_deleted(self) -> None:
        """测试删除方法判断."""
        method = MethodChange(
            class_name="com.example.Service",
            method_name="oldMethod",
            change_type=ChangeType.DELETE,
        )
        assert method.is_deleted is True
        assert method.is_new is False


class TestFileChange:
    """FileChange测试类."""

    def test_is_java_file(self) -> None:
        """测试Java文件判断."""
        java_file = FileChange(file_path="src/main/java/Service.java")
        txt_file = FileChange(file_path="README.txt")

        assert java_file.is_java_file is True
        assert txt_file.is_java_file is False

    def test_is_test_file(self) -> None:
        """测试文件判断."""
        test_file = FileChange(file_path="src/test/java/ServiceTest.java")
        main_file = FileChange(file_path="src/main/java/Service.java")

        assert test_file.is_test_file is True
        assert main_file.is_test_file is False

    def test_total_changes(self) -> None:
        """测试总变更行数计算."""
        file = FileChange(
            file_path="Service.java",
            insertions=10,
            deletions=5,
        )
        assert file.total_changes == 15

    def test_method_changes(self) -> None:
        """测试方法变更列表."""
        method1 = MethodChange(
            class_name="Service",
            method_name="method1",
        )
        method2 = MethodChange(
            class_name="Service",
            method_name="method2",
        )
        file = FileChange(
            file_path="Service.java",
            method_changes=[method1, method2],
        )
        assert len(file.method_changes) == 2


class TestCommitInfo:
    """CommitInfo测试类."""

    def test_short_hash(self) -> None:
        """测试短哈希."""
        commit = CommitInfo(
            hash="abcdef1234567890",
            message="Test commit",
            author="Test Author",
            email="test@example.com",
            timestamp=datetime.now(),
        )
        assert commit.short_hash == "abcdef1"

    def test_short_hash_short_input(self) -> None:
        """测试短哈希输入."""
        commit = CommitInfo(
            hash="abc",
            message="Test",
            author="Test",
            email="test@test.com",
            timestamp=datetime.now(),
        )
        assert commit.short_hash == "abc"

    def test_short_hash_empty_input(self) -> None:
        """空哈希应返回空字符串而不是异常."""
        commit = CommitInfo(
            hash="",
            message="Test",
            author="Test",
            email="test@test.com",
            timestamp=datetime.now(),
        )
        assert commit.short_hash == ""

    def test_title(self) -> None:
        """测试提交标题."""
        commit = CommitInfo(
            hash="abc123",
            message="First line\nSecond line\nThird line",
            author="Test",
            email="test@test.com",
            timestamp=datetime.now(),
        )
        assert commit.title == "First line"

    def test_title_empty_and_newlines(self) -> None:
        """空消息或仅换行应返回空标题."""
        commit_empty = CommitInfo(
            hash="abc123",
            message="",
            author="Test",
            email="test@test.com",
            timestamp=datetime.now(),
        )
        commit_newlines = CommitInfo(
            hash="abc123",
            message="\n\n",
            author="Test",
            email="test@test.com",
            timestamp=datetime.now(),
        )

        assert commit_empty.title == ""
        assert commit_newlines.title == ""


class TestChangeSet:
    """ChangeSet测试类."""

    def test_changed_files(self) -> None:
        """测试变更文件列表."""
        change_set = ChangeSet(
            file_changes=[
                FileChange(file_path="File1.java"),
                FileChange(file_path="File2.java"),
            ]
        )
        assert change_set.changed_files == ["File1.java", "File2.java"]

    def test_changed_java_files(self) -> None:
        """测试Java文件过滤（包含与排除）。"""
        change_set = ChangeSet(
            file_changes=[
                FileChange(file_path="Service.java"),
                FileChange(file_path="README.md"),
                FileChange(file_path="Config.java"),
                FileChange(file_path="Service.java.bak"),
                FileChange(file_path="docs/test.txt"),
            ]
        )

        assert "Service.java" in change_set.changed_java_files
        assert "Config.java" in change_set.changed_java_files
        assert "README.md" not in change_set.changed_java_files
        assert "Service.java.bak" not in change_set.changed_java_files
        assert "docs/test.txt" not in change_set.changed_java_files
        assert len(change_set.changed_java_files) == 2

    def test_changed_methods(self) -> None:
        """测试变更方法列表与格式."""
        change_set = ChangeSet(
            file_changes=[
                FileChange(
                    file_path="Service.java",
                    method_changes=[
                        MethodChange(
                            class_name="com.example.Service",
                            method_name="method1",
                        ),
                        MethodChange(
                            class_name="com.example.Service",
                            method_name="method2",
                            signature="(String)",
                        ),
                    ],
                ),
            ]
        )
        methods = change_set.changed_methods
        assert len(methods) == 2
        assert "com.example.Service.method1" in methods
        assert "com.example.Service.method2(String)" in methods
        for method in methods:
            assert "." in method
            assert len(method.split(".")) >= 3

    def test_total_insertions_and_deletions(self) -> None:
        """测试总增删行数."""
        change_set = ChangeSet(
            file_changes=[
                FileChange(file_path="File1.java", insertions=10, deletions=5),
                FileChange(file_path="File2.java", insertions=20, deletions=10),
            ]
        )
        assert change_set.total_insertions == 30
        assert change_set.total_deletions == 15

    def test_commit_count(self) -> None:
        """测试提交数量."""
        change_set = ChangeSet(
            commits=[
                CommitInfo(
                    hash="abc",
                    message="Commit 1",
                    author="Test",
                    email="test@test.com",
                    timestamp=datetime.now(),
                ),
                CommitInfo(
                    hash="def",
                    message="Commit 2",
                    author="Test",
                    email="test@test.com",
                    timestamp=datetime.now(),
                ),
            ]
        )
        assert change_set.commit_count == 2

    def test_get_file_change(self) -> None:
        """测试获取文件变更."""
        file_change = FileChange(file_path="Service.java")
        change_set = ChangeSet(file_changes=[file_change])

        found = change_set.get_file_change("Service.java")
        not_found = change_set.get_file_change("NotFound.java")

        assert found == file_change
        assert not_found is None

    def test_add_file_change(self) -> None:
        """测试添加文件变更."""
        change_set = ChangeSet()
        file_change = FileChange(file_path="New.java")

        change_set.add_file_change(file_change)

        assert len(change_set.file_changes) == 1
        assert change_set.file_changes[0] == file_change

    def test_is_empty(self) -> None:
        """测试空变更集判断."""
        empty_set = ChangeSet()
        non_empty_set = ChangeSet(file_changes=[FileChange(file_path="File.java")])

        assert empty_set.is_empty() is True
        assert non_empty_set.is_empty() is False

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        change_set = ChangeSet(
            from_commit="abc123",
            to_commit="def456",
            commits=[
                CommitInfo(
                    hash="h1",
                    message="m1",
                    author="a",
                    email="e",
                    timestamp=datetime.now(),
                )
            ],
            file_changes=[
                FileChange(
                    file_path="File.java",
                    insertions=10,
                    deletions=5,
                    method_changes=[
                        MethodChange(class_name="C", method_name="m"),
                    ],
                ),
            ],
        )
        data = change_set.to_dict()

        assert data["from_commit"] == "abc123"
        assert data["to_commit"] == "def456"
        assert data["commit_count"] == 1
        assert data["total_insertions"] == 10
        assert data["total_deletions"] == 5
        assert data["changed_files"] == ["File.java"]
        assert data["changed_methods"] == ["C.m"]
