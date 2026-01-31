"""Setup configuration for JCIA."""

from setuptools import find_packages, setup

setup(
    name="jcia",
    version="0.1.0",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    install_requires=[
        "click>=8.1.0",
        "pydriller>=2.6.0",
        "pyyaml>=6.0.1",
        "jinja2>=3.1.2",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "rich>=13.7.0",
        "pydantic>=2.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "ruff>=0.1.0",
            "pyright>=1.1.340",
            "bandit[toml]>=1.7.6",
            "pre-commit>=3.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "jcia=jcia.cli:main",
        ],
    },
    python_requires=">=3.10",
)
