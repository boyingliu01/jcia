"""测试发布守卫 check_dist_placeholders（issue #20-B）."""

import gzip
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts import check_dist_placeholders as guard
from scripts.check_dist_placeholders import PLACEHOLDER_RE, check


def _write_zip_container(path: Path, members: dict[str, bytes]) -> None:
    """把 members 写成一个 zip 容器（wheel 与 zip 形式 sdist 共用）.

    Args:
        path: 容器文件路径。
        members: 成员名到内容的映射。
    """
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def _write_tar_container(path: Path, members: dict[str, bytes]) -> None:
    """把 members 写成一个 tar.gz 容器.

    Args:
        path: 容器文件路径。
        members: 成员名到内容的映射。
    """
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


class TestCheckDistPlaceholders:
    """测试 check_dist_placeholders.check 的扫描行为."""

    def test_guard_source_is_self_clean(self) -> None:
        """守卫源码自身不得含会被它拦截的字符串（防自咬）."""
        source = Path(guard.__file__).read_text(encoding="utf-8")

        assert PLACEHOLDER_RE.search(source) is None

    def test_clean_wheel_yields_no_hits(self, tmp_path: Path) -> None:
        """干净的 wheel 不产生任何命中."""
        dist = tmp_path / "dist"
        dist.mkdir()
        _write_zip_container(dist / "demo-1.0-py3-none-any.whl", {"demo/__init__.py": b"x = 1\n"})

        assert check(dist) == []

    def test_wheel_placeholder_is_reported_with_location(self, tmp_path: Path) -> None:
        """wheel 成员内的占位地址被抓出，并给出成员名与行号."""
        dist = tmp_path / "dist"
        dist.mkdir()
        _write_zip_container(
            dist / "demo-1.0-py3-none-any.whl",
            {"demo-1.0.dist-info/METADATA": b"Author: Fake <fake@example.com>\n"},
        )

        hits = check(dist)

        assert len(hits) == 1
        assert "METADATA:1:" in hits[0]

    def test_zip_sdist_placeholder_is_reported(self, tmp_path: Path) -> None:
        """zip 形式的 sdist 按 zip 容器扫描."""
        dist = tmp_path / "dist"
        dist.mkdir()
        _write_zip_container(
            dist / "demo-1.0.zip", {"demo/PKG-INFO": b"Home: https://example.org\n"}
        )

        hits = check(dist)

        assert len(hits) == 1
        assert "example.org" in hits[0]

    def test_tar_sdist_placeholder_is_reported(self, tmp_path: Path) -> None:
        """tar.gz 形式 sdist 的成员同样被扫描."""
        dist = tmp_path / "dist"
        dist.mkdir()
        _write_tar_container(
            dist / "demo-1.0.tar.gz",
            {"demo-1.0/README.md": b"support: help@example.net\n"},
        )

        hits = check(dist)

        assert len(hits) == 1
        assert "README.md" in hits[0]

    def test_unrecognized_artifact_fails_closed(self, tmp_path: Path) -> None:
        """无法识别的产物即使内容干净也必须阻断（fail-closed）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "mystery.bin").write_bytes(b"no address here\n")

        hits = check(dist)

        assert any("unrecognized artifact type" in hit for hit in hits)

    def test_unrecognized_gzip_artifact_is_scanned_best_effort(self, tmp_path: Path) -> None:
        """无法识别的 gzip 帧被透明解压后尽力扫描."""
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "mystery.bin").write_bytes(gzip.compress(b"mail: a@example.com\n"))

        hits = check(dist)

        assert any("example.com" in hit for hit in hits)
        assert any("unrecognized artifact type" in hit for hit in hits)

    def test_missing_dist_dir_raises(self, tmp_path: Path) -> None:
        """dist 目录不存在时报错而非静默通过."""
        with pytest.raises(FileNotFoundError, match="not found"):
            check(tmp_path / "dist")

    def test_empty_dist_dir_raises(self, tmp_path: Path) -> None:
        """dist 目录为空时报错而非静默通过."""
        dist = tmp_path / "dist"
        dist.mkdir()

        with pytest.raises(FileNotFoundError, match="no artifacts"):
            check(dist)


class TestMainExitCodes:
    """测试 main() 的退出码映射."""

    def test_main_ok_returns_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """无命中时退出码为 0."""

        def _fake_check() -> list[str]:
            return []

        monkeypatch.setattr(guard, "check", _fake_check)

        assert guard.main() == 0

    def test_main_blocks_on_hits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """有命中时退出码为 1."""

        def _fake_check() -> list[str]:
            return ["boom"]

        monkeypatch.setattr(guard, "check", _fake_check)

        assert guard.main() == 1

    def test_main_reports_error_as_nonzero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """无法读取产物时退出码为 1."""

        def _fake_check() -> list[str]:
            raise FileNotFoundError("no dist")

        monkeypatch.setattr(guard, "check", _fake_check)

        assert guard.main() == 1
