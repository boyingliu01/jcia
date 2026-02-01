"""LocalFileSystemService 文件读写单元测试."""

from __future__ import annotations

from pathlib import Path

import pytest

from jcia.infrastructure.fs.file_system import LocalFileSystemService


class TestLocalFileSystemService:
    """文件系统读写行为测试."""

    def test_write_and_read_text_creates_parents(self, tmp_path: Path) -> None:
        """写文本应自动创建父目录并可读取回原文."""
        fs = LocalFileSystemService(base_dir=tmp_path)

        target_rel = Path("nested/dir/file.txt")
        fs.write_text(target_rel, "hello", encoding="utf-8")

        content = fs.read_text(target_rel, encoding="utf-8")

        assert content == "hello"
        assert (tmp_path / target_rel).exists()

    def test_write_and_read_bytes(self, tmp_path: Path) -> None:
        """写入与读取二进制内容应保持一致."""
        fs = LocalFileSystemService(base_dir=tmp_path)
        data = b"\x01\x02demo"
        fs.write_bytes("bin/data.bin", data)

        loaded = fs.read_bytes("bin/data.bin")

        assert loaded == data

    def test_exists_and_remove_is_idempotent(self, tmp_path: Path) -> None:
        """exists 与 remove 应正确反映文件存在性且可幂等删除."""
        fs = LocalFileSystemService(base_dir=tmp_path)
        fs.write_text("a.txt", "hi")

        assert fs.exists("a.txt") is True
        assert fs.remove_file("a.txt") is True
        assert fs.exists("a.txt") is False
        assert fs.remove_file("a.txt") is False

    def test_read_missing_raises_file_not_found(self, tmp_path: Path) -> None:
        """读取不存在的文件应抛出 FileNotFoundError."""
        fs = LocalFileSystemService(base_dir=tmp_path)

        with pytest.raises(FileNotFoundError):
            fs.read_text("missing.txt")

    def test_ensure_dir_is_idempotent(self, tmp_path: Path) -> None:
        """ensure_dir 多次调用应安全且目录存在."""
        fs = LocalFileSystemService(base_dir=tmp_path)

        created = fs.ensure_dir("logs/archive")
        created_again = fs.ensure_dir("logs/archive")

        assert created.exists()
        assert created.is_dir()
        assert created_again == created
