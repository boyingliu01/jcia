"""测试 wheel 资源守卫 check_wheel_assets（issue #20-C）."""

import io
import sys
import tarfile
import types
import zipfile
from pathlib import Path

import pytest

from scripts import check_wheel_assets as guard
from scripts.check_wheel_assets import check

REPO_ROOT = Path(__file__).resolve().parents[3]

WHEEL_PREFIX = "jcia/reports/templates/"
SDIST_PREFIX = "demo-1.0/"


def _write_wheel(path: Path, members: dict[str, bytes]) -> None:
    """把 members 写成一个最小 wheel 容器.

    Args:
        path: 容器文件路径。
        members: 成员名到内容的映射。
    """
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def _write_sdist(path: Path, prefix: str, members: dict[str, bytes]) -> None:
    """把 members 写成一个最小 sdist（tar.gz）容器.

    Args:
        path: 容器文件路径。
        prefix: 包内顶层前缀（如 "demo-1.0/"）。
        members: 前缀下成员名到内容的映射。
    """
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name=prefix + name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def _config(source_dir: Path, package_roots: tuple[str, ...] = ()) -> guard.GuardConfig:
    """构造注入用的 GuardConfig（单资源目录 + 单 sdist 候选前缀）.

    Args:
        source_dir: 作为资源来源的临时目录。
        package_roots: .py 对账的包根（默认空元组，不启用对账范围）。

    Returns:
        GuardConfig: 供 check() 注入的契约对象。
    """
    return guard.GuardConfig(
        resource_dirs=((source_dir, WHEEL_PREFIX),),
        package_roots=package_roots,
        sdist_prefix_candidates=(SDIST_PREFIX,),
        repo_root=source_dir.parent,
    )


def _pyproject(tmp_path: Path, body: str) -> Path:
    """把给定 TOML 正文写成临时 pyproject.toml 并返回其路径.

    Args:
        tmp_path: 测试临时目录。
        body: pyproject.toml 的完整文本内容。

    Returns:
        Path: 写出的 pyproject.toml 路径。
    """
    path = tmp_path / "pyproject.toml"
    path.write_text(body, encoding="utf-8")
    return path


class TestCheckWheelAssets:
    """测试 check_wheel_assets.check 的断言行为."""

    def test_all_resources_packaged(self, tmp_path: Path) -> None:
        """资源文件进入 wheel 与 sdist 时检查通过（双产物）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "demo-1.0-py3-none-any.whl",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )
        _write_sdist(
            dist / "demo-1.0.tar.gz",
            SDIST_PREFIX,
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )

        assert check(dist, _config(source)) == []

    def test_missing_resource_is_reported(self, tmp_path: Path) -> None:
        """源目录存在而 wheel 缺失的资源被抓出，消息含成员路径与 wheel 名."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/__init__.py": b"x = 1\n"})
        _write_sdist(
            dist / "demo-1.0.tar.gz",
            SDIST_PREFIX,
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )

        misses = check(dist, _config(source))

        assert len(misses) == 1
        assert WHEEL_PREFIX + "page.html" in misses[0]
        assert "demo-1.0-py3-none-any.whl" in misses[0]
        assert "source:" in misses[0]

    def test_dotfiles_are_exempt(self, tmp_path: Path) -> None:
        """点文件（如 .gitkeep 占位）不要求进入 wheel 与 sdist（双断言）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / ".gitkeep").write_text("", encoding="utf-8")
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/__init__.py": b"x = 1\n"})
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})

        assert check(dist, _config(source)) == []

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
        _write_sdist(
            dist / "demo-1.0.tar.gz",
            SDIST_PREFIX,
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )

        misses = check(dist, _config(source))

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
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})

        with pytest.raises(ValueError, match="declared resource directory"):
            check(dist, _config(tmp_path / "absent"))

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
        _write_sdist(
            dist / "demo-1.0.tar.gz",
            SDIST_PREFIX,
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )

        misses = check(dist, _config(source))

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
        _write_sdist(
            dist / "demo-1.0.tar.gz",
            SDIST_PREFIX,
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )

        assert check(dist, _config(source)) == []

    def test_members_are_read_once_per_artifact(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """每个产物只打开一次：成员读取在 (wheel x 目录) 循环外（REQ-04）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        sources = [tmp_path / "first", tmp_path / "second"]
        for source in sources:
            source.mkdir()
            (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "a-1.0-py3-none-any.whl",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )
        _write_wheel(
            dist / "b-1.0-py3-none-any.whl",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )
        _write_sdist(
            dist / "demo-1.0.tar.gz",
            SDIST_PREFIX,
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )
        config = guard.GuardConfig(
            resource_dirs=tuple((source, WHEEL_PREFIX) for source in sources),
            package_roots=(),
            sdist_prefix_candidates=(SDIST_PREFIX,),
            repo_root=tmp_path,
        )
        wheel_reads: list[str] = []
        sdist_reads: list[str] = []
        real_wheel_members = guard._wheel_members
        real_sdist_members = guard._sdist_members

        def spy_wheel_members(artifact: Path) -> set[str]:
            wheel_reads.append(artifact.name)
            return real_wheel_members(artifact)

        def spy_sdist_members(artifact: Path) -> set[str]:
            sdist_reads.append(artifact.name)
            return real_sdist_members(artifact)

        monkeypatch.setattr(guard, "_wheel_members", spy_wheel_members)
        monkeypatch.setattr(guard, "_sdist_members", spy_sdist_members)

        assert check(dist, config) == []
        assert sorted(wheel_reads) == ["a-1.0-py3-none-any.whl", "b-1.0-py3-none-any.whl"]
        assert sdist_reads == ["demo-1.0.tar.gz"]


class TestSdistAssets:
    """测试 check_wheel_assets.check 的 sdist 正向断言（REQ-06）."""

    def test_sdist_missing_resource_is_reported(self, tmp_path: Path) -> None:
        """sdist 缺少已声明资源时被指名，消息含 sdist 名与成员路径（AC-12）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "demo-1.0-py3-none-any.whl",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})

        misses = check(dist, _config(source))

        assert len(misses) == 1
        assert SDIST_PREFIX + WHEEL_PREFIX + "page.html" in misses[0]
        assert "demo-1.0.tar.gz" in misses[0]

    def test_sdist_prefix_mismatch_raises(self, tmp_path: Path) -> None:
        """sdist top-level 前缀与全部候选不匹配时 fail-closed（AC-13）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "demo-1.0-py3-none-any.whl",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )
        _write_sdist(
            dist / "demo-1.0.tar.gz",
            "stale-9.9/",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )

        with pytest.raises(ValueError, match="not recognized") as excinfo:
            check(dist, _config(source))

        message = str(excinfo.value)
        assert SDIST_PREFIX in message
        assert "stale-9.9/" in message

    def test_sdist_leading_dot_slash_members_are_matched(self, tmp_path: Path) -> None:
        """tar 成员名前导 './' 剥离后 sdist 前缀与资源匹配成功（AC-14）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "demo-1.0-py3-none-any.whl",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )
        _write_sdist(
            dist / "demo-1.0.tar.gz",
            "./" + SDIST_PREFIX,
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )

        assert check(dist, _config(source)) == []

    def test_sdist_py_members_do_not_participate_in_reverse_check(self, tmp_path: Path) -> None:
        """sdist 中源码树不存在的 .py 成员不触发反向 stale 报警（DD-06）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "demo-1.0-py3-none-any.whl",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )
        _write_sdist(
            dist / "demo-1.0.tar.gz",
            SDIST_PREFIX,
            {
                WHEEL_PREFIX + "page.html": b"<html></html>",
                "jcia/foo.py": b"x = 1\n",
            },
        )

        assert check(dist, _config(source)) == []

    def test_dist_without_sdist_raises(self, tmp_path: Path) -> None:
        """dist 中没有 sdist 时报错而非静默跳过，提示全量构建命令（AC-15）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (source / "page.html").write_text("<html></html>", encoding="utf-8")
        _write_wheel(
            dist / "demo-1.0-py3-none-any.whl",
            {WHEEL_PREFIX + "page.html": b"<html></html>"},
        )

        with pytest.raises(FileNotFoundError, match="python -m build"):
            check(dist, _config(source))


class TestPyReconciliation:
    """测试 wheel 内 .py 成员对源码树的单向对账（REQ-02）."""

    def test_stale_py_member_is_reported(self, tmp_path: Path) -> None:
        """wheel 中源码树不存在的 .py 成员被识别为陈旧残留（产物->源码）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (tmp_path / "demo").mkdir()
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/ghost.py": b"x = 1\n"})
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})

        misses = check(dist, _config(source, package_roots=("demo",)))

        assert len(misses) == 1
        assert "demo/ghost.py" in misses[0]
        assert "demo-1.0-py3-none-any.whl" in misses[0]
        assert "absent from" in misses[0]

    def test_source_backed_py_members_do_not_trigger(self, tmp_path: Path) -> None:
        """源码树中存在的 .py 成员不误报."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (tmp_path / "demo").mkdir()
        (tmp_path / "demo" / "app.py").write_text("x = 1\n", encoding="utf-8")
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/app.py": b"x = 1\n"})
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})

        assert check(dist, _config(source, package_roots=("demo",))) == []

    def test_non_source_members_are_excluded(self, tmp_path: Path) -> None:
        """dist-info 成员、__pycache__ 内成员、顶层散落 .py 均不参与对账."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (tmp_path / "demo").mkdir()
        _write_wheel(
            dist / "demo-1.0-py3-none-any.whl",
            {
                "demo/__pycache__/ghost.cpython-312.pyc": b"\x00",
                "demo/__pycache__/ghost.py": b"x = 1\n",
                "demo-1.0.dist-info/METADATA": b"Metadata-Version: 2.1\n",
                "demo-1.0.dist-info/stray.py": b"x = 1\n",
                "loose.py": b"x = 1\n",
            },
        )
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})

        assert check(dist, _config(source, package_roots=("demo",))) == []

    def test_source_less_allowlist_exempts_members(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """白名单中的无源码 .py 成员被豁免（预留常量生效）."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        (tmp_path / "demo").mkdir()
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/generated.py": b"x = 1\n"})
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})
        monkeypatch.setattr(guard, "_SOURCE_LESS_PY_ALLOWLIST", frozenset({"demo/generated.py"}))

        assert check(dist, _config(source, package_roots=("demo",))) == []

    def test_dotdot_member_name_is_reported(self, tmp_path: Path) -> None:
        """含 '..' 段的成员名不安全，报错而非按路径拼接."""
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/../evil.py": b"x = 1\n"})
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})

        misses = check(dist, _config(source, package_roots=("demo",)))

        assert len(misses) == 1
        assert "demo/../evil.py" in misses[0]
        assert "unsafe" in misses[0]

    def test_backslash_member_name_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """含反斜杠的成员名不安全（Windows 下会被当作分隔符），报错.

        成员名经注入而非真实写入：Windows 上 zipfile 在读写两侧都会把
        "\\" 归一化为 "/"（_sanitize_filename 依赖 os.sep），即使手工构造
        字面名字节，namelist() 也不再返回原名；Linux（发布流水线）读取时
        保留原名。注入使该分支在任一平台上都被真实执行。
        """
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/keep.py": b"x = 1\n"})
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})
        monkeypatch.setattr(guard, "_wheel_members", lambda _artifact: {"demo\\evil.py"})

        misses = check(dist, _config(source, package_roots=("demo",)))

        assert len(misses) == 1
        assert "demo\\evil.py" in misses[0]
        assert "unsafe" in misses[0]

    def test_absolute_member_name_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """绝对路径成员名不安全（joinpath 会用其丢弃基准目录），报错而非按路径拼接.

        成员名经注入：与反斜杠用例同理，不依赖平台对 zip 成员名的规范化差异，
        使该分支在任一平台上都被真实执行。
        """
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/keep.py": b"x = 1\n"})
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})
        monkeypatch.setattr(guard, "_wheel_members", lambda _artifact: {"/etc/evil.py"})

        misses = check(dist, _config(source, package_roots=("demo",)))

        assert len(misses) == 1
        assert "/etc/evil.py" in misses[0]
        assert "absolute" in misses[0]

    def test_colon_member_name_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """含 ':' 段的成员名（盘符形态）不安全，报错而非按路径拼接.

        成员名经注入：不依赖平台对 zip 成员名的规范化差异，使该分支在任一
        平台上都被真实执行。
        """
        dist = tmp_path / "dist"
        dist.mkdir()
        source = tmp_path / "templates"
        source.mkdir()
        _write_wheel(dist / "demo-1.0-py3-none-any.whl", {"demo/keep.py": b"x = 1\n"})
        _write_sdist(dist / "demo-1.0.tar.gz", SDIST_PREFIX, {"demo/__init__.py": b"x = 1\n"})
        monkeypatch.setattr(guard, "_wheel_members", lambda _artifact: {"jcia/C:/evil.py"})

        misses = check(dist, _config(source, package_roots=("jcia",)))

        assert len(misses) == 1
        assert "jcia/C:/evil.py" in misses[0]
        assert "unsafe" in misses[0]


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

    def test_main_maps_toml_decode_error_to_exit_one(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TOML 损坏（TOMLDecodeError ⊂ ValueError）映射退出码 1（REQ-01 边界）."""

        def _fake_check() -> list[str]:
            guard._toml_loader().loads("not [[[ valid")
            return []

        monkeypatch.setattr(guard, "check", _fake_check)

        assert guard.main() == 1
        assert "wheel asset guard error" in capsys.readouterr().out

    @pytest.mark.parametrize(
        "error",
        [
            tarfile.TarError("truncated sdist"),
            zipfile.BadZipFile("truncated wheel"),
        ],
        ids=["tar-error", "bad-zip"],
    )
    def test_main_maps_archive_errors_to_exit_one(
        self, monkeypatch: pytest.MonkeyPatch, error: Exception
    ) -> None:
        """损坏归档（TarError / BadZipFile）映射退出码 1."""

        def _fake_check() -> list[str]:
            raise error

        monkeypatch.setattr(guard, "check", _fake_check)

        assert guard.main() == 1

    def test_main_maps_import_error_to_exit_one(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TOML 解析器缺失（ImportError）映射退出码 1 且保留安装指引."""

        def _fake_check() -> list[str]:
            raise ImportError("TOML 解析器不可用：请安装 dev extra（含 tomli）")

        monkeypatch.setattr(guard, "check", _fake_check)

        assert guard.main() == 1
        assert "tomli" in capsys.readouterr().out

    def test_main_maps_type_error_to_exit_one(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """配置类型错误（TypeError，如 packages 条目非字符串）映射退出码 1."""

        def _fake_check() -> list[str]:
            raise TypeError("[tool.setuptools].packages entry must be a string: 1")

        monkeypatch.setattr(guard, "check", _fake_check)

        assert guard.main() == 1
        assert "wheel asset guard error" in capsys.readouterr().out


class TestGuardConfigNormalization:
    """测试 GuardConfig 构造期的路径归一化契约（M4）."""

    def test_relative_resource_dir_is_anchored_at_repo_root(self, tmp_path: Path) -> None:
        """相对资源目录在构造期归一化为 repo_root 锚定的绝对路径."""
        config = guard.GuardConfig(
            resource_dirs=((Path("templates"), WHEEL_PREFIX),),
            package_roots=(),
            sdist_prefix_candidates=(SDIST_PREFIX,),
            repo_root=tmp_path,
        )

        assert config.resource_dirs == ((tmp_path / "templates", WHEEL_PREFIX),)

    def test_absolute_resource_dir_passes_through(self, tmp_path: Path) -> None:
        """绝对资源目录原样保留（注入形态）."""
        absolute = tmp_path / "templates"
        config = guard.GuardConfig(
            resource_dirs=((absolute, WHEEL_PREFIX),),
            package_roots=(),
            sdist_prefix_candidates=(SDIST_PREFIX,),
            repo_root=tmp_path,
        )

        assert config.resource_dirs == ((absolute, WHEEL_PREFIX),)

    def test_relative_repo_root_is_rejected(self) -> None:
        """repo_root 非绝对路径时 fail-closed（归一化不得依赖 CWD）."""
        with pytest.raises(ValueError, match="absolute"):
            guard.GuardConfig(
                resource_dirs=(),
                package_roots=(),
                sdist_prefix_candidates=(),
                repo_root=Path("relative"),
            )


class TestTomlLoader:
    """测试 _toml_loader 的三态可用性契约（REQ-01）."""

    def test_loader_works_in_current_environment(self) -> None:
        """常态：真实运行环境可取得 TOML 解析器（3.11+ tomllib / 3.10 tomli）."""
        loader = guard._toml_loader()

        assert hasattr(loader, "loads")

    def test_loader_falls_back_to_tomli(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """回退态：tomllib 不可用时改用 tomli（3.10 路径）."""
        fake_tomli = types.ModuleType("tomli")
        fake_tomli.loads = lambda text: {"stub": True}  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "tomllib", None)
        monkeypatch.setitem(sys.modules, "tomli", fake_tomli)

        assert guard._toml_loader() is fake_tomli

    def test_loader_raises_when_both_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """双缺态：两个解析器都不可用时 ImportError 且消息含安装指引."""
        monkeypatch.setitem(sys.modules, "tomllib", None)
        monkeypatch.setitem(sys.modules, "tomli", None)

        with pytest.raises(ImportError, match="tomli"):
            guard._toml_loader()


class TestDeriveResourceDirs:
    """测试 _derive_resource_dirs 的派生与 fail-closed 契约（REQ-01）."""

    def test_derive_from_real_repository_pyproject(self) -> None:
        """真实仓库 pyproject 派生出与 package-data 声明一致的资源目录（lock test）."""
        data = guard._load_pyproject(REPO_ROOT / "pyproject.toml")

        assert guard._derive_resource_dirs(data, REPO_ROOT) == (
            (Path("jcia/reports/templates"), "jcia/reports/templates/"),
        )

    def test_derive_merges_multiple_keys_and_values(self, tmp_path: Path) -> None:
        """多个包键/多个模式值合并为多条 (源目录, wheel 前缀) 声明且保序."""
        (tmp_path / "pkg_a" / "res").mkdir(parents=True)
        (tmp_path / "pkg_b" / "data").mkdir(parents=True)
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.package-data]
pkg_a = ["res/*"]
pkg_b = ["data/*"]
""",
        )

        derived = guard._derive_resource_dirs(guard._load_pyproject(path), tmp_path)

        assert derived == (
            (Path("pkg_a/res"), "pkg_a/res/"),
            (Path("pkg_b/data"), "pkg_b/data/"),
        )

    def test_derive_maps_dotted_key_to_package_path(self, tmp_path: Path) -> None:
        """点号包键映射为目录路径（K.replace('.', '/')）."""
        (tmp_path / "demo" / "sub" / "res").mkdir(parents=True)
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.package-data]
"demo.sub" = ["res/*"]
""",
        )

        derived = guard._derive_resource_dirs(guard._load_pyproject(path), tmp_path)

        assert derived == ((Path("demo/sub/res"), "demo/sub/res/"),)

    def test_derive_rejects_wildcard_key(self, tmp_path: Path) -> None:
        """包键含通配符时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.package-data]
"pkg*" = ["res/*"]
""",
        )

        with pytest.raises(ValueError, match="wildcard"):
            guard._derive_resource_dirs(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_non_glob_value(self, tmp_path: Path) -> None:
        """模式值不是 <rel>/* 形态时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.package-data]
pkg = ["res/page.html"]
""",
        )

        with pytest.raises(ValueError, match="pattern"):
            guard._derive_resource_dirs(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_bare_star_value(self, tmp_path: Path) -> None:
        """模式值仅有 '/*'（相对目录为空）时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.package-data]
pkg = ["/*"]
""",
        )

        with pytest.raises(ValueError, match="pattern"):
            guard._derive_resource_dirs(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_nested_wildcard_value(self, tmp_path: Path) -> None:
        """模式值在目录部分夹带通配符时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.package-data]
pkg = ["res/**/*"]
""",
        )

        with pytest.raises(ValueError, match="pattern"):
            guard._derive_resource_dirs(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_empty_values(self, tmp_path: Path) -> None:
        """包键声明空列表时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.package-data]
pkg = []
""",
        )

        with pytest.raises(ValueError, match="non-empty"):
            guard._derive_resource_dirs(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_missing_package_data_table(self, tmp_path: Path) -> None:
        """package-data 表缺失（空集）时 fail-closed."""
        path = _pyproject(tmp_path, '[project]\nname = "demo"\nversion = "1.0"\n')

        with pytest.raises(ValueError, match="package-data"):
            guard._derive_resource_dirs(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_missing_resource_directory(self, tmp_path: Path) -> None:
        """声明的资源目录在源码树中不存在时 fail-closed 且消息含条目原文."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.package-data]
ghost = ["res/*"]
""",
        )

        with pytest.raises(ValueError, match="not found"):
            guard._derive_resource_dirs(guard._load_pyproject(path), tmp_path)


class TestDerivePackageRoots:
    """测试 _derive_package_roots 的派生与 exclude 三重规则（REQ-01/REQ-02）."""

    def test_derive_from_real_repository_pyproject(self) -> None:
        """真实仓库 pyproject 派生包根为 ('jcia',)（lock test：include=jcia*, exclude=tests*）."""
        data = guard._load_pyproject(REPO_ROOT / "pyproject.toml")

        assert guard._derive_package_roots(data, REPO_ROOT) == ("jcia",)

    def test_derive_strips_trailing_dot_from_prefix(self, tmp_path: Path) -> None:
        """include 前缀去尾点（jcia.* -> jcia）."""
        (tmp_path / "jcia").mkdir()
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = ["jcia.*"]
""",
        )

        assert guard._derive_package_roots(guard._load_pyproject(path), tmp_path) == ("jcia",)

    def test_derive_rejects_subpackage_pattern(self, tmp_path: Path) -> None:
        """include 前缀含点（子包 pattern）时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = ["jcia.tools*"]
""",
        )

        with pytest.raises(ValueError, match="top-level"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_root_wildcard(self, tmp_path: Path) -> None:
        """include 前缀为空（裸通配符）时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = ["*"]
""",
        )

        with pytest.raises(ValueError, match="empty"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_allows_subpackage_exclude(self, tmp_path: Path) -> None:
        """exclude 命中合法子包前缀（jcia.tests*）时通过且包根不变."""
        (tmp_path / "jcia").mkdir()
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = ["jcia*"]
exclude = ["jcia.tests*"]
""",
        )

        assert guard._derive_package_roots(guard._load_pyproject(path), tmp_path) == ("jcia",)

    def test_derive_rejects_exclude_ancestor_overlap(self, tmp_path: Path) -> None:
        """exclude 前缀是包根的祖先（j*）时 fail-closed."""
        (tmp_path / "jcia").mkdir()
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = ["jcia*"]
exclude = ["j*"]
""",
        )

        with pytest.raises(ValueError, match="exclude"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_exclude_equal_to_package_root(self, tmp_path: Path) -> None:
        """exclude 前缀等于包根（jcia*）时 fail-closed."""
        (tmp_path / "jcia").mkdir()
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = ["jcia*"]
exclude = ["jcia*"]
""",
        )

        with pytest.raises(ValueError, match="exclude"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_empty_exclude_pattern(self, tmp_path: Path) -> None:
        """exclude 前缀为空（裸通配符）时 fail-closed."""
        (tmp_path / "jcia").mkdir()
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = ["jcia*"]
exclude = ["*"]
""",
        )

        with pytest.raises(ValueError, match="exclude"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_missing_package_directory(self, tmp_path: Path) -> None:
        """派生出的包根在源码树中不存在时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = ["ghost*"]
""",
        )

        with pytest.raises(ValueError, match="package root"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_empty_include(self, tmp_path: Path) -> None:
        """include 为空列表（空集）时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = []
""",
        )

        with pytest.raises(ValueError, match="no package roots"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_falls_back_to_explicit_packages(self, tmp_path: Path) -> None:
        """find 缺失时读 [tool.setuptools].packages 显式列表（顶层段、保序去重）."""
        (tmp_path / "demo").mkdir()
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools]
packages = ["demo", "demo.sub", "demo"]
""",
        )

        assert guard._derive_package_roots(guard._load_pyproject(path), tmp_path) == ("demo",)

    def test_derive_rejects_wildcard_in_packages_fallback(self, tmp_path: Path) -> None:
        """回退列表项含通配符时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools]
packages = ["demo*"]
""",
        )

        with pytest.raises(ValueError, match="wildcard"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_empty_first_segment_in_packages_fallback(self, tmp_path: Path) -> None:
        """回退列表项首个点前段落为空时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools]
packages = [".demo"]
""",
        )

        with pytest.raises(ValueError, match="empty"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_missing_packages_configuration(self, tmp_path: Path) -> None:
        """find 与 packages 均缺失（空集）时 fail-closed."""
        path = _pyproject(tmp_path, '[project]\nname = "demo"\nversion = "1.0"\n')

        with pytest.raises(ValueError, match="no package roots"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_non_root_where(self, tmp_path: Path) -> None:
        """find.where 非 ["."]（src-layout）时 fail-closed 而非误报包根不存在."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
where = ["src"]
include = ["jcia*"]
""",
        )

        with pytest.raises(ValueError, match="flat layout"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_string_include(self, tmp_path: Path) -> None:
        """include 为字符串（非列表）时 fail-closed，而非逐字符迭代."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = "jcia*"
""",
        )

        with pytest.raises(ValueError, match="list"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_non_string_include_entry(self, tmp_path: Path) -> None:
        """include 元素非字符串时 fail-closed（ValueError 而非 AttributeError）."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools.packages.find]
include = [1]
""",
        )

        with pytest.raises(ValueError, match="string"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)

    def test_derive_rejects_non_string_packages_fallback_entry(self, tmp_path: Path) -> None:
        """packages 回退列表元素非字符串时 fail-closed."""
        path = _pyproject(
            tmp_path,
            """
[tool.setuptools]
packages = [1]
""",
        )

        with pytest.raises(TypeError, match="string"):
            guard._derive_package_roots(guard._load_pyproject(path), tmp_path)


class TestDeriveSdistPrefixCandidates:
    """测试 _derive_sdist_prefix_candidates 的候选集派生（REQ-06）."""

    def test_candidates_from_real_repository_pyproject(self) -> None:
        """真实仓库派生候选含原始名（jcia 无归一化差异，三形式合一；lock test）."""
        data = guard._load_pyproject(REPO_ROOT / "pyproject.toml")
        name = data["project"]["name"]
        version = data["project"]["version"]

        assert guard._derive_sdist_prefix_candidates(data) == (f"{name}-{version}/",)

    def test_candidates_cover_name_normalization_variants(self) -> None:
        """原始/PEP503/下划线三种名称形式均生成候选且按序去重."""
        data = {"project": {"name": "My-Pkg_Name.v2", "version": "0.9"}}

        assert guard._derive_sdist_prefix_candidates(data) == (
            "My-Pkg_Name.v2-0.9/",
            "my-pkg-name-v2-0.9/",
            "my_pkg_name_v2-0.9/",
        )

    def test_candidates_reject_missing_project_table(self) -> None:
        """[project] 表缺失时 fail-closed."""
        with pytest.raises(ValueError, match="project"):
            guard._derive_sdist_prefix_candidates({})

    def test_candidates_reject_missing_name_or_version(self) -> None:
        """[project] 缺 name/version 时 fail-closed 且消息含缺失键名."""
        with pytest.raises(ValueError, match="version"):
            guard._derive_sdist_prefix_candidates({"project": {"name": "demo"}})


class TestLoadConfig:
    """测试 _load_config 与 _default_pyproject_path 的装配契约."""

    def test_load_config_from_real_repository(self) -> None:
        """真实仓库装配出完整 GuardConfig（含归一化后的绝对资源目录；lock test）.

        lock test：本断言锁定真实仓库配置，pyproject 变更须同步。
        """
        config = guard._load_config(REPO_ROOT / "pyproject.toml")
        version = guard._load_pyproject(REPO_ROOT / "pyproject.toml")["project"]["version"]

        assert config.repo_root == REPO_ROOT
        assert config.resource_dirs == (
            (REPO_ROOT / "jcia/reports/templates", "jcia/reports/templates/"),
        )
        assert config.package_roots == ("jcia",)
        assert config.sdist_prefix_candidates == (f"jcia-{version}/",)

    def test_load_config_rejects_missing_file(self, tmp_path: Path) -> None:
        """pyproject 文件缺失时报 FileNotFoundError 且消息含路径."""
        with pytest.raises(FileNotFoundError, match="not found"):
            guard._load_config(tmp_path / "absent.toml")

    def test_load_config_rejects_invalid_toml(self, tmp_path: Path) -> None:
        """TOML 损坏时抛 TOMLDecodeError（main 映射退出码 1）."""
        path = _pyproject(tmp_path, "not [[[ valid toml")
        decode_error = guard._toml_loader().TOMLDecodeError

        with pytest.raises(decode_error):
            guard._load_config(path)

    def test_default_pyproject_path_is_repo_relative(self) -> None:
        """默认 pyproject 路径为仓库根相对路径 pyproject.toml."""
        assert guard._default_pyproject_path() == Path("pyproject.toml")


class TestPyprojectDevExtra:
    """测试 pyproject 的 3.10 TOML 回退依赖声明（REQ-01）."""

    def test_dev_extra_pins_tomli_below_python_311(self) -> None:
        """dev extra 声明 tomli 条件依赖（py < 3.11；lock test：仓库配置变更须同步）."""
        data = guard._load_pyproject(REPO_ROOT / "pyproject.toml")
        dev = data["project"]["optional-dependencies"]["dev"]

        assert any("tomli" in entry and "python_version < '3.11'" in entry for entry in dev)
