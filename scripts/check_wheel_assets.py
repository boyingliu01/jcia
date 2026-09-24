"""Guard built wheels against silently dropped package resources.

setuptools packages ``.py`` modules automatically but ignores every other file
inside a package unless it matches a ``[tool.setuptools.package-data]`` glob.
An undeclared resource -- or one excluded by glob semantics (``*`` does not
match dot files such as ``.gitkeep``) -- is therefore dropped from the wheel
with no warning from ``python -m build`` or ``twine check``. The staleness is
discovered only by an end user when the missing file is accessed at runtime
(issue #20-C).

This module is the missing gate: after the build it asserts four things --
every real file under each declared resource directory is present inside every
wheel in ``dist/`` (drop guard) and inside every sdist, plus two reverse
reconciliations against the source tree: every top-level member under the
declared wheel prefix must map back to a real source file, and every wheel
member under a package root ending in ``.py`` must exist in the source tree
(stale-cache guards: setuptools reuses ``build/lib`` incrementally, so a file
deleted from the source tree can keep being packed into the wheel with no
warning). Both reverse directions deliberately cover wheels only: a sdist
tree also carries files the wheel never ships.

Resource directories and the sdist prefix candidates are derived from
``pyproject.toml``, and the check compares against the filesystem fact instead
of re-running the glob that setuptools runs: re-running the same glob would
repeat any glob hole on the expectation side as well, quietly cancelling the
check.

Invoked from ``.github/workflows/release.yml`` and usable locally with::

    python -m build && python scripts/check_wheel_assets.py

Scope notes:

* Dot files are treated as placeholders/metadata (``.gitkeep`` merely keeps an
  empty directory alive in git) and are exempt. Verified empirically: the
  declared ``*`` glob skips them and the wheel is valid without them.
* Only top-level files of a resource dir are asserted, matching the declared
  pattern ``reports/templates/*`` whose ``*`` does not descend into
  subdirectories. A future subdirectory needs its own entry in
  ``[tool.setuptools.package-data]``.
* A resource directory named here but missing from the source tree is a
  configuration error and fails the check rather than being skipped.
* Only ``*.tar.gz`` sdists are recognized -- the shape ``python -m build``
  produces. A ``.tgz``/``.zip`` archive fails as "no sdist found" instead of
  being silently accepted. ``check_dist_placeholders.py`` scans a wider set of
  shapes because it must classify every file in ``dist/`` against a different
  threat (leaked placeholder contacts), not because that wider set is a
  supported release shape.
* The guard's CLI entry point is anchored at the process working directory
  (``dist/`` and the default ``pyproject.toml`` path are CWD-relative): run
  ``main()`` from the repository root. The ``GuardConfig`` API itself
  normalizes resource dirs against an absolute ``repo_root`` at construction
  time, so injected configs carry no CWD dependence.
* Member names are compared as strings; on case-insensitive filesystems an
  ``is_file()`` probe can match a case-variant name. Kept explicit rather
  than normalized -- acceptable for a source-tree reconciliation.
"""

from __future__ import annotations

import re
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import ModuleType

DIST_DIR = Path("dist")

# Wheel members that legitimately exist without a source counterpart
# (generated modules). Empty today: a source-less ``.py`` member is a failure
# by default, and adding an entry here is an explicit reviewable exemption --
# never a silent skip.
_SOURCE_LESS_PY_ALLOWLIST: frozenset[str] = frozenset()


@dataclass(frozen=True)
class GuardConfig:
    """Contract between the source tree and the built artifacts.

    Derived once from ``pyproject.toml`` so the guard and the packaging
    configuration cannot drift apart.

    Attributes:
        resource_dirs: Pairs of (source directory, wheel-internal prefix)
            that declare which files each source dir must supply. Relative
            entries are normalized to absolute, ``repo_root``-anchored paths
            at construction time.
        package_roots: Top-level package roots the ``.py`` reconciliation
            scopes itself to.
        sdist_prefix_candidates: Candidate top-level prefixes a sdist archive
            may use for the project tree (original / normalized name forms).
        repo_root: Directory containing the pyproject file; the anchor for
            every path derived above. Must be an absolute path.
    """

    resource_dirs: tuple[tuple[Path, str], ...]
    package_roots: tuple[str, ...]
    sdist_prefix_candidates: tuple[str, ...]
    repo_root: Path

    def __post_init__(self) -> None:
        """Normalize resource dirs to absolute, ``repo_root``-anchored paths.

        The derived configuration carries repository-relative paths while
        injected configurations may pass absolute ones; normalizing once here
        keeps :func:`check` on a single code path instead of re-deciding the
        anchor at every use site.

        Raises:
            ValueError: If ``repo_root`` is not absolute -- normalization
                would then depend on the process working directory.
        """
        if not self.repo_root.is_absolute():
            raise ValueError(f"repo_root must be an absolute path: {self.repo_root}")
        object.__setattr__(
            self,
            "resource_dirs",
            tuple(
                (directory if directory.is_absolute() else self.repo_root / directory, prefix)
                for directory, prefix in self.resource_dirs
            ),
        )


def _toml_loader() -> ModuleType:
    """Return an available TOML parser module.

    The imports live inside the function on purpose: every call re-executes
    them, so ``sys.modules`` is consulted at call time. That keeps the
    fallback genuinely testable -- setting a ``sys.modules`` entry to None
    reproduces the "module unavailable" condition (official Python semantics:
    a None entry makes ``import`` raise ImportError).

    The form is fixed to ``import tomllib`` (module object); never switch to
    ``from tomllib import loads``, which would silently defeat that mechanism.

    Returns:
        ModuleType: ``tomllib`` on Python >= 3.11, otherwise the ``tomli``
        backport (declared as a conditional dev dependency).

    Raises:
        ImportError: If neither parser can be imported.
    """
    try:
        import tomllib  # type: ignore[import-not-found]

        return tomllib
    except ImportError:
        pass
    try:
        import tomli  # type: ignore[import-not-found]

        return tomli
    except ImportError as exc:
        raise ImportError(
            "TOML 解析器不可用：Python>=3.11 自带 tomllib；"
            "3.10 请安装 dev extra（pip install -e '.[dev]'，含 tomli）"
        ) from exc


def _load_pyproject(path: Path) -> dict[str, Any]:
    """Read and parse a pyproject.toml file.

    Args:
        path: Path to the pyproject.toml file.

    Returns:
        dict[str, Any]: Parsed top-level TOML table.

    Raises:
        FileNotFoundError: If the file does not exist.
        TOMLDecodeError: If the file content is not valid TOML.
    """
    if not path.is_file():
        raise FileNotFoundError(f"pyproject file not found: {path}")
    return _toml_loader().loads(path.read_text(encoding="utf-8"))


def _literal_prefix(pattern: str) -> str:
    """Return the literal text before the first ``*`` in a glob pattern.

    Args:
        pattern: A setuptools-style glob pattern (``*`` is the only wildcard
            the guard understands).

    Returns:
        str: The pattern itself when it contains no wildcard.
    """
    star = pattern.find("*")
    return pattern if star < 0 else pattern[:star]


def _derive_resource_dirs(
    pyproject: dict[str, Any], repo_root: Path
) -> tuple[tuple[Path, str], ...]:
    """Derive (source directory, wheel prefix) pairs from package-data.

    The guard reads ``[tool.setuptools.package-data]`` -- the single source of
    truth -- instead of keeping a hand-copied list in this module. Supported
    shape: an entry key is a package dotted path and every declared pattern is
    ``<relative-dir>/*`` (exactly one trailing wildcard, no other wildcard).
    Anything else is a configuration the guard cannot assert safely, so it
    fails closed rather than guessing.

    Args:
        pyproject: Parsed pyproject.toml top-level table.
        repo_root: Repository root the package directories resolve against.

    Returns:
        tuple[tuple[Path, str], ...]: (repository-relative source dir, wheel
        prefix) pairs in declaration order; ``GuardConfig`` normalizes the
        directories to absolute paths at construction time.

    Raises:
        ValueError: If the table is missing/empty, an entry is malformed, or a
            declared source directory does not exist in the source tree.
    """
    tool_table = pyproject.get("tool") or {}
    setuptools_table = tool_table.get("setuptools") or {}
    package_data = setuptools_table.get("package-data")
    if not isinstance(package_data, dict) or not package_data:
        raise ValueError(
            "no packaged resource directories declared in [tool.setuptools.package-data]"
        )

    derived: list[tuple[Path, str]] = []
    for key, patterns in package_data.items():
        if "*" in key:
            raise ValueError(f"package-data key cannot contain wildcards: {key!r}")
        package_dir = key.replace(".", "/")
        if not isinstance(patterns, list) or not patterns:
            raise ValueError(
                f"package-data entry must declare a non-empty list of patterns: {key!r}"
            )
        for pattern in patterns:
            shape_ok = (
                isinstance(pattern, str)
                and pattern.endswith("/*")
                and "*" not in pattern[:-2]
                and bool(pattern[:-2])
            )
            if not shape_ok:
                raise ValueError(
                    f"package-data pattern must look like '<dir>/*': {key!r} -> {pattern!r}"
                )
            relative_dir = pattern[:-2]
            source_dir = Path(package_dir) / relative_dir
            if not (repo_root / source_dir).is_dir():
                raise ValueError(
                    f"declared resource directory not found: {source_dir} "
                    f"(entry: {key!r} -> {pattern!r})"
                )
            derived.append((source_dir, f"{package_dir}/{relative_dir}/"))
    return tuple(derived)


def _validated_patterns(table: dict[str, Any], key: str) -> list[str]:
    """Return ``find.<key>`` as a validated list of pattern strings.

    The guard fails closed on shapes it cannot assert: a bare string would be
    iterated character by character, and a non-string entry would surface as
    ``AttributeError`` deep in prefix extraction instead of a configuration
    error.

    Args:
        table: The ``[tool.setuptools.packages.find]`` table.
        key: Either ``"include"`` or ``"exclude"``.

    Returns:
        list[str]: The validated entries; empty when the key is absent.

    Raises:
        ValueError: If the value is present but not a list of strings.
    """
    value = table.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
        raise ValueError(f"find.{key} must be a list of pattern strings: {value!r}")
    return value


def _derive_package_roots(pyproject: dict[str, Any], repo_root: Path) -> tuple[str, ...]:
    """Derive the top-level package roots the guard's scopes may cover.

    Roots come from ``[tool.setuptools.packages.find]`` include patterns (the
    literal prefix before the first wildcard, minus a trailing dot). When the
    find table is absent, the explicit ``[tool.setuptools].packages`` list is
    used instead (first dot-segment of each entry, order preserved,
    de-duplicated). Only a flat layout is supported: ``find.where`` must be
    absent or ``["."]``, since any other value (src layout) would make the
    derived roots resolve against the wrong directory.

    Exclude patterns are validated in three tiers so a configuration that
    could hide an entire package root from the guard's scope fails closed
    while a legitimate subpackage exclusion stays accepted: an empty literal
    prefix is rejected; a prefix starting with ``<root>.`` (subpackage scope,
    cannot hide the root itself) is accepted; a prefix that ``<root>``
    startswith (equal to or an ancestor of a root) is rejected.

    Args:
        pyproject: Parsed pyproject.toml top-level table.
        repo_root: Repository root the package roots resolve against.

    Returns:
        tuple[str, ...]: Top-level package roots in declaration order.

    Raises:
        TypeError: If a ``[tool.setuptools].packages`` entry is not a string
            (invalid types follow the ``TypeError`` convention).
        ValueError: If no roots can be derived, an entry is malformed, the
            layout is not flat, or a derived root does not exist under
            ``repo_root``.
    """
    setuptools_table = (pyproject.get("tool") or {}).get("setuptools") or {}
    packages_setting = setuptools_table.get("packages")

    roots: list[str] = []
    if isinstance(packages_setting, dict) and isinstance(packages_setting.get("find"), dict):
        find_table = packages_setting["find"]
        where = find_table.get("where")
        if where is not None and where != ["."]:
            raise ValueError(
                "only a flat layout is supported "
                f'([tool.setuptools.packages.find].where = ["."]), got: {where!r}'
            )
        for pattern in _validated_patterns(find_table, "include"):
            prefix = _literal_prefix(pattern).rstrip(".")
            if not prefix:
                raise ValueError(f"find.include entry has an empty literal prefix: {pattern!r}")
            if "." in prefix:
                raise ValueError(
                    f"find.include entry must reference top-level packages only: {pattern!r}"
                )
            roots.append(prefix)
        for pattern in _validated_patterns(find_table, "exclude"):
            prefix = _literal_prefix(pattern)
            if not prefix:
                raise ValueError(f"find.exclude entry has an empty literal prefix: {pattern!r}")
            for root in roots:
                if prefix.startswith(root + "."):
                    continue  # subpackage scope: cannot hide the root itself
                if root.startswith(prefix):
                    raise ValueError(
                        f"find.exclude may exclude a whole package root: {pattern!r} "
                        f"(root {root!r})"
                    )
    elif isinstance(packages_setting, list):
        for entry in packages_setting:
            if not isinstance(entry, str):
                raise TypeError(f"[tool.setuptools].packages entry must be a string: {entry!r}")
            if "*" in entry:
                raise ValueError(
                    f"[tool.setuptools].packages entry cannot contain wildcards: {entry!r}"
                )
            top_segment = entry.split(".", 1)[0]
            if not top_segment:
                raise ValueError(
                    f"[tool.setuptools].packages entry has an empty first segment: {entry!r}"
                )
            roots.append(top_segment)

    roots = list(dict.fromkeys(roots))
    if not roots:
        raise ValueError(
            "no package roots derived from [tool.setuptools.packages.find] "
            "or [tool.setuptools].packages"
        )
    for root in roots:
        if not (repo_root / root).is_dir():
            raise ValueError(
                f"derived package root not found in source tree: {root!r} (under {repo_root})"
            )
    return tuple(roots)


def _derive_sdist_prefix_candidates(pyproject: dict[str, Any]) -> tuple[str, ...]:
    """Derive the candidate top-level prefixes a sdist may use.

    Build backends name the sdist tree ``<name>-<version>/``; normalization
    differs across backends, so the candidates cover the declared name plus
    the PEP 503 (dash) and underscore normalized forms, de-duplicated. The
    candidate set is deliberately conservative rather than exhaustive: a
    mismatch fails closed. Only static version declarations are supported
    (dynamic versions such as setuptools-scm are outside the scope).

    Args:
        pyproject: Parsed pyproject.toml top-level table.

    Returns:
        tuple[str, ...]: Candidate prefixes ending with a slash.

    Raises:
        ValueError: If the [project] table or its name/version keys are
            missing (message names the missing keys).
    """
    project = pyproject.get("project")
    missing: list[str] = []
    if not isinstance(project, dict):
        missing.append("[project] table")
        project = {}
    else:
        missing.extend(
            key
            for key, value in (("name", project.get("name")), ("version", project.get("version")))
            if not value
        )
    if missing:
        raise ValueError(
            f"pyproject is missing required key(s) for sdist prefix derivation: {', '.join(missing)}"
        )
    name = project["name"]
    version = project["version"]
    candidates = dict.fromkeys(
        [
            f"{name}-{version}/",
            f"{re.sub(r'[-_.]+', '-', name).lower()}-{version}/",
            f"{re.sub(r'[-_.]+', '_', name).lower()}-{version}/",
        ]
    )
    return tuple(candidates)


def _load_config(pyproject_path: Path) -> GuardConfig:
    """Load the guard contract derived from a pyproject.toml file.

    Args:
        pyproject_path: Path to the pyproject.toml file.

    Returns:
        GuardConfig: Derived contract; every path is anchored at the
        directory that contains the pyproject file.
    """
    data = _load_pyproject(pyproject_path)
    repo_root = pyproject_path.resolve().parent
    return GuardConfig(
        resource_dirs=_derive_resource_dirs(data, repo_root),
        package_roots=_derive_package_roots(data, repo_root),
        sdist_prefix_candidates=_derive_sdist_prefix_candidates(data),
        repo_root=repo_root,
    )


def _default_pyproject_path() -> Path:
    """Return the default pyproject.toml path (repository-root relative)."""
    return Path("pyproject.toml")


def _wheel_members(artifact: Path) -> set[str]:
    """Return the member names contained in a wheel.

    Args:
        artifact: Path to the ``.whl`` file.

    Returns:
        set[str]: Member names as recorded in the zip central directory.
    """
    with zipfile.ZipFile(artifact) as archive:
        return set(archive.namelist())


def _sdist_members(artifact: Path) -> set[str]:
    """Return the member names contained in a sdist archive.

    ``tarfile`` records members exactly as stored; some tools emit a leading
    ``./`` on every path. Stripping that prefix keeps the member shape
    identical to the wheel members returned by :func:`_wheel_members`, so
    prefix matching and the resource assertions see one canonical form.

    Args:
        artifact: Path to the ``.tar.gz`` file.

    Returns:
        set[str]: Member names without a leading ``./``.
    """
    with tarfile.open(artifact) as archive:
        members = archive.getnames()
    return {name[2:] if name.startswith("./") else name for name in members}


def _match_sdist_prefix(artifact: Path, members: set[str], config: GuardConfig) -> str:
    """Match the observed sdist tree prefix against the candidate set.

    The candidate set (:func:`_derive_sdist_prefix_candidates`) is
    deliberately not exhaustive: it covers the declared name plus the known
    normalization variants, and a mismatch fails closed instead of guessing
    (the conservative direction for a release gate). A stale ``dist/`` from
    an earlier version is the common cause of a mismatch -- remove it
    (``rm -rf dist``) and rebuild with ``python -m build``.

    Args:
        artifact: Path to the ``.tar.gz`` file (used in diagnostics).
        members: Normalized member names of the archive.
        config: Guard contract holding the candidate prefixes.

    Returns:
        str: The matched candidate (with trailing slash).

    Raises:
        ValueError: If no candidate matches the archive's top-level
            prefixes; the message lists both the candidates and the
            prefixes actually observed.
    """
    top_level = {member.split("/", 1)[0] + "/" for member in members if "/" in member}
    for candidate in config.sdist_prefix_candidates:
        if candidate in top_level:
            return candidate
    raise ValueError(
        f"sdist top-level prefix not recognized in {artifact.name}: "
        f"candidates {sorted(config.sdist_prefix_candidates)}, "
        f"observed {sorted(top_level)} "
        "(stale dist from an earlier version? remove dist/ and rebuild with `python -m build`)"
    )


def _unsafe_member_reason(member: str) -> str | None:
    """Return why a wheel member name is unsafe to join onto a directory.

    Threat model: member names are POSIX-form relative paths (ZIP APPNOTE
    4.4.17.1 requires forward slashes and forbids drive letters). A name that
    breaks the assumption is reported instead of being resolved: on Windows
    ``joinpath`` would treat a backslash as a separator, a ``:`` segment as a
    drive reference (resetting the base to a drive-relative path), and an
    absolute path or a ``..`` segment would escape the directory the member
    is joined onto.

    Args:
        member: Member name as recorded in the zip central directory.

    Returns:
        str | None: A human-readable reason, or None when the name is safe.
    """
    if "\\" in member:
        return "contains a backslash"
    if ":" in member:
        return "contains a ':' segment (drive-letter form)"
    path = PurePosixPath(member)
    if path.is_absolute():
        return "is an absolute path"
    if ".." in path.parts:
        return "contains a '..' segment"
    return None


def check(dist_dir: Path = DIST_DIR, config: GuardConfig | None = None) -> list[str]:
    """Collect resources that are absent from any built artifact.

    Four assertions run against every artifact in ``dist_dir``:

    * Forward, wheels: every real file under each declared resource directory
      must be present inside every wheel under the declared wheel prefix.
    * Forward, sdists: the same files must be present inside every sdist
      under the archive's matched top-level tree prefix.
    * Reverse, wheels only: every top-level member under the declared wheel
      prefix must map back to a real source file (stale build cache guard).
      Sdists deliberately take no part in the reverse direction: their tree
      also carries files the wheel never ships.
    * Reverse ``.py``, wheels only: every wheel member under a declared
      package root that ends in ``.py`` must exist in the source tree (the
      same stale build cache guard, applied to modules). This direction is
      deliberately one-way: a stale cache only ever adds members, while a
      source module dropped from the wheel is guarded by setuptools package
      discovery and would surface loudly as ``ImportError`` at import time,
      not silently. Assumes modules are shipped through setuptools package
      discovery; a namespace-package or custom ``build_py`` setup must
      revisit this assumption.

    Member names are assumed to be POSIX-form relative paths; a name that is
    not (absolute path, backslash separator, ``:`` drive-letter segment,
    ``..`` segment) is reported as unsafe and excluded from path joining.

    Documented boundaries: ``.dist-info`` members, stray top-level ``.py``
    files, members outside the declared package roots, ``__pycache__``
    leftovers, and stale non-``.py`` files nested under a resource prefix are
    not asserted. Generated source-less modules are reported by default;
    exempt them explicitly via ``_SOURCE_LESS_PY_ALLOWLIST``.

    The guard assumes the release pipeline builds both artifacts in one full
    ``python -m build`` run; a dist directory missing either artifact kind
    fails closed rather than being silently accepted.

    Every artifact is read exactly once, before the resource-directory
    loops: member lists do not depend on the resource directory, so
    re-reading them per directory would repeat identical work.

    Args:
        dist_dir: Directory holding the built distribution artifacts.
        config: Guard contract; when omitted it is derived from the
            repository pyproject file.

    Returns:
        list[str]: One description per missing or stale resource; empty when
        every declared resource is present in every artifact.

    Raises:
        FileNotFoundError: If ``dist_dir`` does not exist or holds no wheel
            or no sdist.
        ValueError: If a declared resource directory is absent from the
            source tree, or a sdist top-level prefix matches none of the
            candidate set (a stale ``dist/`` from an earlier version is the
            common cause -- remove ``dist/`` and rebuild).
        ImportError: If no TOML parser is available when the configuration
            has to be loaded.
        tarfile.TarError: If a sdist archive cannot be read (corrupt or
            truncated).
        zipfile.BadZipFile: If a wheel cannot be read (corrupt or truncated).
        OSError: If an artifact cannot be opened at the filesystem level.
    """
    if config is None:
        config = _load_config(_default_pyproject_path())
    if not dist_dir.is_dir():
        raise FileNotFoundError(f"dist directory not found: {dist_dir}")

    wheels = sorted(path for path in dist_dir.iterdir() if path.is_file() and path.suffix == ".whl")
    if not wheels:
        raise FileNotFoundError(f"no wheel found in {dist_dir}")
    sdists = sorted(
        path for path in dist_dir.iterdir() if path.is_file() and path.name.endswith(".tar.gz")
    )
    if not sdists:
        raise FileNotFoundError(
            f"no sdist found in {dist_dir} (run `python -m build` to build both artifacts)"
        )

    members_by_wheel = {wheel: _wheel_members(wheel) for wheel in wheels}
    members_by_sdist = {sdist: _sdist_members(sdist) for sdist in sdists}
    sdist_prefixes = {
        sdist: _match_sdist_prefix(sdist, members_by_sdist[sdist], config) for sdist in sdists
    }

    misses: list[str] = []
    for resolved_source_dir, wheel_prefix in config.resource_dirs:
        # GuardConfig normalizes every entry to an absolute, repo_root-anchored
        # path at construction time; this check still covers injected configs
        # whose directories are missing, while derivation-time validation
        # emits the richer entry-context error.
        if not resolved_source_dir.is_dir():
            raise ValueError(f"declared resource directory not found: {resolved_source_dir}")
        # Forward collection deliberately skips dot files (the declared ``*``
        # glob does not match them), while the reverse direction built on the
        # _wheel_members listing accepts any top-level member whose name maps
        # to a real file via is_file(). A packaged dot file is therefore
        # neither required nor flagged as stale -- an intentional asymmetry.
        resources = sorted(
            path
            for path in resolved_source_dir.iterdir()
            if path.is_file() and not path.name.startswith(".")
        )
        for wheel, members in members_by_wheel.items():
            for resource in resources:
                member = wheel_prefix + resource.name
                if member not in members:
                    misses.append(f"{member} missing from {wheel.name} (source: {resource})")
            # Reverse direction: every top-level member under the prefix must map
            # back to a real file in the source tree. A member with no source
            # counterpart is stale cache fallout (e.g. build/lib kept a copy of a
            # deleted file) and must block the release just like a dropped one.
            for member in sorted(members):
                if not member.startswith(wheel_prefix):
                    continue
                tail = member[len(wheel_prefix) :]
                if not tail or "/" in tail:
                    continue
                if (resolved_source_dir / tail).is_file():
                    continue
                misses.append(
                    f"{member} present in {wheel.name} but absent from "
                    f"{resolved_source_dir} (stale build cache?)"
                )
        for sdist, members in members_by_sdist.items():
            for resource in resources:
                member = f"{sdist_prefixes[sdist]}{wheel_prefix}{resource.name}"
                if member not in members:
                    misses.append(f"{member} missing from {sdist.name} (source: {resource})")

    # Reverse ``.py`` reconciliation (artifact -> source tree, wheels only).
    # setuptools reuses ``build/lib`` incrementally, so a module deleted from
    # the source tree can keep riding along in the wheel with no warning. The
    # name-safety validation runs for every member, before any scoping filter:
    # a backslash name such as ``demo\evil.py`` would never match ``demo/``
    # and would otherwise slip through silently.
    for wheel, members in members_by_wheel.items():
        for member in sorted(members):
            unsafe = _unsafe_member_reason(member)
            if unsafe is not None:
                misses.append(
                    f"{member} has an unsafe name in {wheel.name} "
                    f"({unsafe}; wheel members must be POSIX-form relative paths)"
                )
                continue
            if not member.endswith(".py"):
                continue
            parts = PurePosixPath(member).parts
            if "__pycache__" in parts:
                continue
            if not any(member.startswith(root + "/") for root in config.package_roots):
                continue
            if member in _SOURCE_LESS_PY_ALLOWLIST:
                continue
            if config.repo_root.joinpath(*parts).is_file():
                continue
            misses.append(
                f"{member} present in {wheel.name} but absent from "
                f"{config.repo_root} (stale build cache?)"
            )
    return misses


def main() -> int:
    """Run the guard and translate results into a process exit code.

    Configuration problems (missing files, broken TOML, missing TOML parser)
    keep their own messages, while archive-read failures get a distinct
    "cannot inspect artifacts" prefix so a corrupted artifact is not mistaken
    for a configuration error.

    Returns:
        int: 0 when every declared resource is packaged, 1 when a resource is
        missing or the artifacts could not be inspected at all.
    """
    try:
        misses = check()
    except (FileNotFoundError, ImportError, TypeError, ValueError) as exc:
        print(f"wheel asset guard error: {exc}")
        return 1
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"wheel asset guard error: cannot inspect artifacts ({type(exc).__name__}: {exc})")
        return 1

    if misses:
        print("release blocked: wheel content violates declared packaged-resource contract:")
        for miss in misses:
            print(f"  {miss}")
        return 1

    print(
        "wheel asset guard OK: declared packaged-resource contract holds for "
        "dist/*.whl and dist/*.tar.gz"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
