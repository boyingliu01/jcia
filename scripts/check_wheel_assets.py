#!/usr/bin/env python
"""Guard built wheels against silently dropped package resources.

setuptools packages ``.py`` modules automatically but ignores every other file
inside a package unless it matches a ``[tool.setuptools.package-data]`` glob.
An undeclared resource -- or one excluded by glob semantics (``*`` does not
match dot files such as ``.gitkeep``) -- is therefore dropped from the wheel
with no warning from ``python -m build`` or ``twine check``. The staleness is
discovered only by an end user when the missing file is accessed at runtime
(issue #20-C).

This module is the missing gate: after the build it asserts two directions --
every real file under each declared resource directory is present inside every
wheel in ``dist/`` (drop guard), and every top-level member under the declared
wheel prefix maps back to a real source file (stale-cache guard: setuptools
reuses ``build/lib`` incrementally, so a file deleted from the source tree can
keep being packed into the wheel with no warning).

Resource directories are listed explicitly (source dir -> wheel prefix) and the
check compares against the filesystem fact instead of re-running the glob that
setuptools runs: re-running the same glob would repeat any glob hole on the
expectation side as well, quietly cancelling the check.

Invoked from ``.github/workflows/release.yml`` and usable locally with::

    python -m build && python scripts/check_wheel_assets.py

Scope notes:

* Dot files are treated as placeholders/metadata (``.gitkeep`` merely keeps an
  empty directory alive in git) and are exempt. Verified empirically: the
  declared ``*`` glob skips them and the wheel is valid without them.
* Only top-level files of a resource dir are asserted, matching the declared
  pattern ``reports/templates/*`` whose ``*`` does not descend into
  subdirectories. A future subdirectory needs its own entry here plus a
  matching package-data pattern.
* A resource directory named here but missing from the source tree is a
  configuration error and fails the check rather than being skipped.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

DIST_DIR = Path("dist")

# (source directory, wheel-internal prefix) for every packaged resource dir.
# Keep in sync with [tool.setuptools.package-data] in pyproject.toml.
PACKAGED_RESOURCE_DIRS: tuple[tuple[Path, str], ...] = (
    (Path("jcia/reports/templates"), "jcia/reports/templates/"),
)


def _wheel_members(artifact: Path) -> set[str]:
    """Return the member names contained in a wheel.

    Args:
        artifact: Path to the ``.whl`` file.

    Returns:
        set[str]: Member names as recorded in the zip central directory.
    """
    with zipfile.ZipFile(artifact) as archive:
        return set(archive.namelist())


def check(
    dist_dir: Path = DIST_DIR,
    resource_dirs: Sequence[tuple[Path, str]] = PACKAGED_RESOURCE_DIRS,
) -> list[str]:
    """Collect resources that are absent from any built wheel.

    Args:
        dist_dir: Directory holding the built distribution artifacts.
        resource_dirs: Pairs of (source directory, wheel-internal prefix) that
            declare which files inside the wheel each source dir must supply.

    Returns:
        list[str]: One description per missing resource; empty when every
        declared resource is present in every wheel.

    Raises:
        FileNotFoundError: If ``dist_dir`` does not exist or holds no wheel.
        ValueError: If a declared resource directory is absent from the source
            tree (stale declaration).
    """
    if not dist_dir.is_dir():
        raise FileNotFoundError(f"dist directory not found: {dist_dir}")

    wheels = sorted(path for path in dist_dir.iterdir() if path.is_file() and path.suffix == ".whl")
    if not wheels:
        raise FileNotFoundError(f"no wheel found in {dist_dir}")

    misses: list[str] = []
    for source_dir, wheel_prefix in resource_dirs:
        if not source_dir.is_dir():
            raise ValueError(f"declared resource directory not found: {source_dir}")
        resources = sorted(
            path
            for path in source_dir.iterdir()
            if path.is_file() and not path.name.startswith(".")
        )
        for wheel in wheels:
            members = _wheel_members(wheel)
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
                if (source_dir / tail).is_file():
                    continue
                misses.append(
                    f"{member} present in {wheel.name} but absent from "
                    f"{source_dir} (stale build cache?)"
                )
    return misses


def main() -> int:
    """Run the guard and translate results into a process exit code.

    Returns:
        int: 0 when every declared resource is packaged, 1 when a resource is
        missing or the wheels could not be inspected at all.
    """
    try:
        misses = check()
    except FileNotFoundError as exc:
        print(f"wheel asset guard error: {exc}")
        return 1
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"wheel asset guard error: cannot inspect wheels ({type(exc).__name__}: {exc})")
        return 1

    if misses:
        print("release blocked: wheel content violates declared packaged-resource contract:")
        for miss in misses:
            print(f"  {miss}")
        return 1

    print("wheel asset guard OK: declared packaged-resource contract holds for dist/*.whl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
