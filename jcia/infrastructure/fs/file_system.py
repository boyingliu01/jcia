"""本地文件系统服务实现."""

from __future__ import annotations

from pathlib import Path

from jcia.core.interfaces.file_system import FileSystemService


class LocalFileSystemService(FileSystemService):
    """基于本地磁盘的文件系统实现."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base_dir = Path(base_dir).resolve() if base_dir else None

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"文件不存在: {target}")
        return target.read_text(encoding=encoding)

    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8") -> Path:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)
        return target

    def read_bytes(self, path: str | Path) -> bytes:
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"文件不存在: {target}")
        return target.read_bytes()

    def write_bytes(self, path: str | Path, content: bytes) -> Path:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    def exists(self, path: str | Path) -> bool:
        return self._resolve(path).exists()

    def ensure_dir(self, path: str | Path) -> Path:
        target = self._resolve(path)
        target.mkdir(parents=True, exist_ok=True)
        return target

    def remove_file(self, path: str | Path) -> bool:
        target = self._resolve(path)
        if target.exists() and target.is_file():
            target.unlink()
            return True
        return False

    def _resolve(self, path: str | Path) -> Path:
        candidate = Path(path)
        if candidate.is_absolute() or self._base_dir is None:
            return candidate
        return (self._base_dir / candidate).resolve()
