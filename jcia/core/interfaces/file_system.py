"""文件系统服务抽象接口."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class FileSystemService(ABC):
    """文件系统读写服务接口."""

    @abstractmethod
    def read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        """读取文本内容."""
        pass

    @abstractmethod
    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8") -> Path:
        """写入文本内容并返回文件路径."""
        pass

    @abstractmethod
    def read_bytes(self, path: str | Path) -> bytes:
        """读取二进制内容."""
        pass

    @abstractmethod
    def write_bytes(self, path: str | Path, content: bytes) -> Path:
        """写入二进制内容并返回文件路径."""
        pass

    @abstractmethod
    def exists(self, path: str | Path) -> bool:
        """判断路径是否存在."""
        pass

    @abstractmethod
    def ensure_dir(self, path: str | Path) -> Path:
        """确保目录存在并返回目录路径."""
        pass

    @abstractmethod
    def remove_file(self, path: str | Path) -> bool:
        """删除文件，不存在时返回 False."""
        pass
