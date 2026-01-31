"""pytest配置和共享fixture."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_git_repo(temp_dir: Path) -> Path:
    """创建模拟的Git仓库."""
    git_dir = temp_dir / ".git"
    git_dir.mkdir()

    # 创建基本的git结构
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    (git_dir / "refs" / "heads").mkdir(parents=True)

    return temp_dir


@pytest.fixture
def sample_java_project(temp_dir: Path) -> Path:
    """创建示例Java项目结构."""
    # 创建Maven项目结构
    pom = temp_dir / "pom.xml"
    pom.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>test-project</artifactId>
    <version>1.0.0</version>
</project>
""")

    # 创建源代码目录
    src_main = temp_dir / "src" / "main" / "java" / "com" / "example"
    src_main.mkdir(parents=True)

    src_test = temp_dir / "src" / "test" / "java" / "com" / "example"
    src_test.mkdir(parents=True)

    return temp_dir


@pytest.fixture
def mock_config(temp_dir: Path) -> MagicMock:
    """创建模拟配置对象."""
    config = MagicMock()
    config.project.name = "test-project"
    config.project.language = "java"
    config.project.build_tool = "maven"
    config.tools.call_graph.jar_path = "/path/to/call-graph.jar"
    config.database.path = str(temp_dir / "test.db")
    return config
