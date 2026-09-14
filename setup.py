"""Packaging shim for JCIA.

All project metadata (name, version, dependencies, optional-dependencies,
console-script entry points) and package discovery are declared in
``pyproject.toml`` (the ``[project]`` and ``[tool.setuptools]`` tables), which
is the single source of truth.

This module intentionally carries no configuration. It exists only so that
legacy tooling invoking ``setup.py`` keeps working; setuptools reads the
authoritative fields from ``pyproject.toml`` when ``build-backend`` is
``setuptools.build_meta``.
"""

from setuptools import setup

setup()
