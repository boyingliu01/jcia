"""测试 wheel 资源守卫 check_wheel_assets（issue #20-C）."""

import zipfile
from pathlib import Path

import pytest

from scripts import check_wheel_assets as guard
from scripts.check_wheel_assets import check

WHEEL_PREFIX = "jcia/reports/templates/"


def _write_wheel(path: Path, members: dict[str, bytes]) -> None:
    """把 members 写成一个最小 wheel 容器.

    Args:
        path: 容器文件路径。
        members: 成员名到内容的映射。
    """
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def _resource_dirs(source_dir: Path) -> tuple[tuple[Path, str], ...]:
    """构造与 package-data 清单同形的 (源目录, wheel 前缀) 声明.

    Args:
        source_dir: 作为资源来源的临时目录。

    Returns:
        tuple[tuple[Path, str], ...]: 单条目声明，前缀与 pyproject 一致。
    """
    return ((source_dir, WHEEL_PREFIX),)


class TestCheckWheelAssets:
    """测试 check_wheel_assets.check 的断言行为."""

    def test_all_resources_packaged(self, tmp_path: Path) -> None:
        """资源文件进入 wheel 时检查通过."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "demo-1.0-py3-none-any.whl",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )

        assert check(dist, _resource_dirs(source)) == []

    def test_missing_resource_is_reported(self, tmp_path: Path) -> None:
        """源目录存在而 wheel 缺失的资源被抓出，消息含成员路径与 wheel 名."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/__init__.py": b"x = 1\n"})

        misses = check(dist, _resource_dirs(source))

        assert len(misses) == 1
        assert WHEEL_PREFIX + "page.html" in misses[0]
        assert "demo-1.0-py3-none-any.whl" in misses[0]
        assert "source:" in misses[0]

    def test_dotfiles_are_exempt(self, tmp_path: Path) -> None:
        """点文件（如 .gitkeep 占位）不要求进入 wheel."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / ".gitkeep").write_text("", encoding="utf-8")
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/__init__.py": b"x = 1\n"})

        assert check(dist, _resource_dirs(source)) == []

    def test_every_wheel_is_checked(self, tmp_path: Path) -> None:
        """dist 中每个 wheel 都必须满足资源断言，缺失方被指名."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "good-1.0-py3-none-any.whl",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )
        _write_wheel(dist / "bad-1.0-py3-none-any.whl", {"demo/__init__.py": b"x = 1\n"})

        misses = check(dist, _resource_dirs(source))

        assert len(misses) == 1
        assert "bad-1.0-py3-none-any.whl" in misses[0]

    def test_missing_dist_dir_raises(self, tmp_path: Path) -> None:
        """dist 目录不存在时报错而非静默通过."""
        with pytest.raises(FileNotFoundError, match="not found"):
            check(tmp_path / "dist")

    def test_dist_without_wheel_raises(self, tmp_path: Path) -> None:
        """dist 中没有 wheel 时报错而非静默通过."""
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "demo-1.0.tar.gz").write_bytes(b"not a zip")

        with pytest.raises(FileNotFoundError, match="no wheel"):
            check(dist)

    def test_missing_declared_source_dir_raises(self, tmp_path: Path) -> None:
        """声明的资源目录在源码树中缺失时按配置错误处理."""
        dist = tmp_path / "dist"
        dist.mkdir()
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/__init__.py": b"x = 1\n"})

        with pytest.raises(ValueError, match="declared resource directory"):
            check(dist, _resource_dirs(tmp_path / "absent"))

    def test_stale_wheel_member_is_reported(self, tmp_path: Path) -> None:
        """wheel 中源码树已不存在的资源被识别为陈旧残留（如 build/lib 缓存）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "demo-1.0-py3-none-any.whl",
            {
                WHEEL_PREFIX + "page.html": b"<html></html>",
                WHEEL_PREFIX + "_probe.html": b"stale",
            },
        )

        misses = check(dist, _resource_dirs(source))

        assert len(misses) == 1
        assert WHEEL_PREFIX + "_probe.html" in misses[0]
        assert "absent from" in misses[0]

    def test_wheel_subdir_members_are_ignored(self, tmp_path: Path) -> None:
        """声明的前缀只覆盖顶层文件：wheel 中前缀下子目录成员不参与反向检查."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "demo-1.0-py3-none-any.whl",
            {
                WHEEL_PREFIX + "page.html": b"<html></html>",
                WHEEL_PREFIX + "nested/deep.html": b"<html></html>",
                WHEEL_PREFIX: b"",
            },
        )

        assert check(dist, _resource_dirs(source)) == []


class TestMainExitCodes:
    """测试 main() 的退出码映射."""

    def test_main_ok_returns_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """无缺失时退出码为 0."""

        def _fake_check() -> list[str]:
            return []

        monkeypatch.setattr(guard, "check", _fake_check)

        assert guard.main() == 0

    def test_main_blocks_on_misses(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """有缺失时退出码为 1."""

        def _fake_check() -> list[str]:
            return ["boom"]

        monkeypatch.setattr(guard, "check", _fake_check)

        assert guard.main() == 1

    def test_main_reports_error_as_nonzero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """无法检查 wheel 时退出码为 1."""

        def _fake_check() -> list[str]:
            raise FileNotFoundError("no dist")

        monkeypatch.setattr(guard, "check", _fake_check)

        assert guard.main() == 1
