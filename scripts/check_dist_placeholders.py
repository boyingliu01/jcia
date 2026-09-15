#!/usr/bin/env python
"""Guard release artifacts against placeholder contact addresses.

A published PyPI release is immutable: the README reaches the project page via
the ``long_description`` carried in ``METADATA`` and can never be edited again
(issuing a yank still keeps the history). A placeholder address that slips
through therefore stays on the public page for the lifetime of the account's
version numbering, and can only be overwritten in the narrative of a later
release.

``twine check`` does not catch this -- it validates metadata syntax only, not
the prose inside a markdown body. This module is the dedicated gate.

It walks every member of each artifact in ``dist/``:

* ``.whl``    -> all zip members (metadata plus installed package sources)
* ``.tar.gz`` -> all regular files (PKG-INFO, README.md, package sources)

Exit code is non-zero and every offending line is listed when a match is found.

Invoked from ``.github/workflows/release.yml`` and usable locally with::

    python -m build && python scripts/check_dist_placeholders.py

Note: this file intentionally lives in ``scripts/``, which is NOT part of the
sdist (verified: the top-level entries of the sdist are LICENSE, PKG-INFO,
README.md, jcia, jcia.egg-info, pyproject.toml, setup.cfg, setup.py). Keeping
the patterns here outside the distributed set stops the guard from matching
its own placeholder literals.
"""

from __future__ import annotations

import re
import sys
import tarfile
import zipfile
from pathlib import Path

# The dot is matched via a character class so that this source file never
# contains a literal string the guard itself would flag.
PLACEHOLDER_RE = re.compile(r"exampl[e]\.(?:org|com|net)", re.IGNORECASE)

DIST_DIR = Path("dist")

MAX_REPORTED_LINE = 100


def _scan_text(artifact: str, member: str, raw: bytes, hits: list[str]) -> None:
    """Record every line of one artifact member that matches the placeholder pattern.

    Args:
        artifact: Path of the artifact being scanned.
        member: Name of the member inside the artifact, or "-" for flat files.
        raw: Raw bytes of the member content.
        hits: Accumulator appended to for each offending line.
    """
    text = raw.decode("utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if PLACEHOLDER_RE.search(line):
            snippet = line.strip()[:MAX_REPORTED_LINE]
            hits.append(f"{artifact}::{member}:{lineno}: {snippet}")


def _scan_wheel(artifact: Path, hits: list[str]) -> None:
    """Scan all members of a wheel, including its ``.dist-info/METADATA``.

    Args:
        artifact: Path to the ``.whl`` file.
        hits: Accumulator appended to for each offending line.
    """
    with zipfile.ZipFile(artifact) as archive:
        for member in archive.namelist():
            if member.endswith("/"):
                continue
            _scan_text(artifact.name, member, archive.read(member), hits)


def _scan_sdist(artifact: Path, hits: list[str]) -> None:
    """Scan all regular files of an sdist tarball.

    Args:
        artifact: Path to the ``.tar.gz`` file.
        hits: Accumulator appended to for each offending line.
    """
    with tarfile.open(artifact) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            _scan_text(artifact.name, member.name, handle.read(), hits)


def check(dist_dir: Path = DIST_DIR) -> list[str]:
    """Collect placeholder hits across every artifact in a dist directory.

    Args:
        dist_dir: Directory holding the built ``.whl`` / ``.tar.gz`` artifacts.

    Returns:
        list[str]: One description per offending line; empty when clean.

    Raises:
        FileNotFoundError: If ``dist_dir`` does not exist.
    """
    if not dist_dir.is_dir():
        raise FileNotFoundError(f"dist directory not found: {dist_dir}")

    artifacts = sorted(path for path in dist_dir.iterdir() if path.suffix in {".whl", ".gz"})
    if not artifacts:
        raise FileNotFoundError(f"no artifacts found in {dist_dir}")

    hits: list[str] = []
    for artifact in artifacts:
        if artifact.name.endswith(".whl"):
            _scan_wheel(artifact, hits)
        elif artifact.name.endswith(".tar.gz"):
            _scan_sdist(artifact, hits)
    return hits


def main() -> int:
    """Run the guard and translate results into a process exit code.

    Returns:
        int: 0 when the artifacts are clean, 1 when placeholders were found.
    """
    try:
        hits = check()
    except FileNotFoundError as exc:
        print(f"placeholder guard error: {exc}")
        return 1

    if hits:
        print("release blocked: placeholder contact found in distribution:")
        for hit in hits:
            print(f"  {hit}")
        return 1

    print("placeholder guard OK: no placeholder contact in dist/*")
    return 0


if __name__ == "__main__":
    sys.exit(main())
