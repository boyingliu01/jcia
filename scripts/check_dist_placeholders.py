"""Guard release artifacts against placeholder contact addresses.

A published PyPI release is immutable: the README reaches the project page via
the ``long_description`` carried in ``METADATA`` and can never be edited again
(issuing a yank still keeps the history). A placeholder address that slips
through therefore stays on the public page for the lifetime of the account's
version numbering, and can only be overwritten in the narrative of a later
release.

``twine check`` does not catch this -- it validates metadata syntax only, not
the prose inside a markdown body. This module is the dedicated gate.

It walks every file in ``dist/`` under a closed classification, because ``publish``
uploads the whole directory and a silently skipped file would be published while
reporting "guard OK":

* ``.whl``               -> all zip members (metadata plus installed package sources)
* ``.tar.gz`` and friends -> all regular files (PKG-INFO, README.md, package sources)
* ``.zip``               -> all zip members (twine accepts a zip-form sdist, so it is
  a supported shape here rather than a hard failure)
* anything else          -> best-effort raw/gunzip scan **plus** a blocking finding: an
  artifact the guard cannot classify is never treated as clean.

Exit code is non-zero and every offending line is listed when a match is found.

Invoked from ``.github/workflows/release.yml`` and usable locally with::

    python -m build && python scripts/check_dist_placeholders.py

Two separate safeguards keep this guard from blocking releases on itself:

* the pattern's character class (see ``PLACEHOLDER_RE``) means this source file
  contains no string the guard would flag, so it never matches itself;
* it sits in ``scripts/``, which is not part of the sdist (verified: the
  top-level entries are LICENSE, PKG-INFO, README.md, jcia, jcia.egg-info,
  pyproject.toml, setup.cfg, setup.py). That placement keeps the sibling
  ``init_test_repo.py`` -- whose git-config fixture uses a real placeholder
  address of the form ``test@example[.]com`` -- out of everything the guard
  scans.
"""

from __future__ import annotations

import gzip
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

# Suffix sets are shared by _classify() and nothing else, so the classifier and
# the dispatcher can no longer drift apart: every name that enters the scan loop
# is guaranteed to land on exactly one branch (or on the fail-closed branch).
_WHEEL_SUFFIXES = (".whl",)
_TAR_SDIST_SUFFIXES = (".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar")
_ZIP_SUFFIXES = (".zip",)


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


def _scan_wheel_container(artifact: Path, hits: list[str]) -> None:
    """Scan all members of a zip-container artifact (wheel or zip-form sdist).

    Args:
        artifact: Path to the ``.whl`` or ``.zip`` file.
        hits: Accumulator appended to for each offending line.
    """
    with zipfile.ZipFile(artifact) as archive:
        for member in archive.namelist():
            if member.endswith("/"):
                continue
            _scan_text(artifact.name, member, archive.read(member), hits)


def _scan_tar_sdist(artifact: Path, hits: list[str]) -> None:
    """Scan all regular files of a tar-form sdist.

    Args:
        artifact: Path to the ``.tar.gz`` or other tar-based file.
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


def _scan_unrecognized(artifact: Path, hits: list[str]) -> None:
    """Best-effort scan of an artifact the classification does not cover.

    The content is scanned anyway -- transparently gunzipping gzip-framed files
    -- so a leak is still reported with its line. The file is then additionally
    recorded as a finding: refusing to classify a published file is safer than
    printing "guard OK" while ``publish`` uploads that same file via ``dist/*``.

    Args:
        artifact: Path to the unclassified file.
        hits: Accumulator appended to for each offending line.
    """
    raw = artifact.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    _scan_text(artifact.name, artifact.name, raw, hits)
    hits.append(f"{artifact.name}::<unrecognized artifact type>: refusing to treat it as clean")


def _classify(name: str) -> str:
    """Map an artifact file name onto one of the supported container kinds.

    Args:
        name: Bare file name of the artifact.

    Returns:
        str: ``"wheel"``, ``"zip_sdist"``, ``"tar_sdist"`` or ``"unknown"``.
    """
    lowered = name.lower()
    if lowered.endswith(_WHEEL_SUFFIXES):
        return "wheel"
    if lowered.endswith(_TAR_SDIST_SUFFIXES):
        return "tar_sdist"
    if lowered.endswith(_ZIP_SUFFIXES):
        return "zip_sdist"
    return "unknown"


def check(dist_dir: Path = DIST_DIR) -> list[str]:
    """Collect placeholder hits across every file in a dist directory.

    Args:
        dist_dir: Directory holding the built distribution artifacts.

    Returns:
        list[str]: One description per offending line, plus one per artifact the
        classification could not name; empty when the directory is clean.

    Raises:
        FileNotFoundError: If ``dist_dir`` does not exist or holds no files.
    """
    if not dist_dir.is_dir():
        raise FileNotFoundError(f"dist directory not found: {dist_dir}")

    artifacts = sorted(path for path in dist_dir.iterdir() if path.is_file())
    if not artifacts:
        raise FileNotFoundError(f"no artifacts found in {dist_dir}")

    hits: list[str] = []
    for artifact in artifacts:
        kind = _classify(artifact.name)
        if kind in {"wheel", "zip_sdist"}:
            _scan_wheel_container(artifact, hits)
        elif kind == "tar_sdist":
            _scan_tar_sdist(artifact, hits)
        else:
            _scan_unrecognized(artifact, hits)
    return hits


def main() -> int:
    """Run the guard and translate results into a process exit code.

    Returns:
        int: 0 when the artifacts are clean, 1 when placeholders were found or
        the artifacts could not be read at all.
    """
    try:
        hits = check()
    except FileNotFoundError as exc:
        print(f"placeholder guard error: {exc}")
        return 1
    except (OSError, ValueError, EOFError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"placeholder guard error: cannot read dist/* ({type(exc).__name__}: {exc})")
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
