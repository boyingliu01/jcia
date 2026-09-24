"""pytest配置和共享fixture."""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Git 在运行 pre-commit 等钩子时会导出 GIT_DIR/GIT_WORK_TREE/GIT_PREFIX 等
# 上下文变量（见 git 文档 githooks(5)）。这些变量会泄漏进以子进程方式创建
# 临时仓库的测试并劫持其 git 操作（例如把文件暂存进真实仓库的索引，或让
# 临时仓库继承宿主的 core.hooksPath）。在 conftest 导入时一次性清理，
# 保证无论以钩子、CI 还是本地方式启动，整个测试会话都运行在干净的 git 环境。
_GIT_CONTEXT_VARS = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
    "GIT_DIR",
    "GIT_GRAFT_FILE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
    "GIT_REPLACE_REF_BASE",
    "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
)
for _var in _GIT_CONTEXT_VARS:
    os.environ.pop(_var, None)


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
    pom.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>test-project</artifactId>
    <version>1.0.0</version>
</project>
"""
    )

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
