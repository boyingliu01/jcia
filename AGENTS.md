# JCIA - Agent Configuration Guide

This guide helps agentic coding agents understand and work effectively with the JCIA (Java Code Impact Analyzer) codebase.

## 📋 Important: Read Project Constitution First

Before making any changes to this codebase, **you must read and follow the PROJECT_CONSTITUTION.md** file. It contains the project's rules for:

- **TDD (Test-Driven Development)** - Red → Green → Refactor cycle
- **CI/CD requirements** - Pre-commit hooks, quality gates, deployment flow
- **Architecture constraints** - Clean Architecture, Dependency Inversion
- **Code quality standards** - Coverage, type safety, error handling

---

## Project Overview

JCIA is a Python tool for analyzing Java code change impact, supporting Maven projects with call chain analysis, test generation, and regression testing. It uses clean architecture principles with clear separation between domain, application, and infrastructure layers.

**Project Stats**: ~2,067 LOC, ~804 test LOC, Python 3.10+

**Development Environment**:
- Requires Python 3.10+
- Uses virtual environment (`.venv`) to avoid PEP 668 externally-managed-environment issues
- Testing should run in PowerShell (Windows) environment
- All scripts assume activation of virtual environment (`.venv\Scripts\activate`)

**Current Progress**: Phase 4/13 completed - Domain Entities & Core Interfaces implemented

---

## 🚨 Critical: TDD Workflow (MANDATORY)

### The TDD Cycle: Red → Green → Refactor

All development in this project **MUST** follow TDD:

#### 1. Write Failing Test (Red)
```python
def test_new_feature_should_work(self) -> None:
    """Test new feature behavior."""
    # Arrange
    change_set = ChangeSet()

    # Act & Assert
    # This will FAIL initially - this is OK!
    assert change_set.some_new_feature() == expected_value
```

Run test and confirm it fails:
```bash
pytest tests/unit/core/test_change_set.py::TestChangeSet::test_new_feature_should_work -v
# Expected: FAILED
```

#### 2. Implement Code to Pass Test (Green)
Write **minimum** code to make test pass:
```python
class ChangeSet:
    def some_new_feature(self) -> str:
        return expected_value  # Simple return just to pass
```

Run test and confirm it passes:
```bash
pytest tests/unit/core/test_change_set.py::TestChangeSet::test_new_feature_should_work -v
# Expected: PASSED
```

#### 3. Refactor While Keeping Tests Green
Improve the implementation without changing behavior:
```python
class ChangeSet:
    def some_new_feature(self) -> str:
        """Calculate feature value."""
        if not self.file_changes:
            return DEFAULT_VALUE
        return self._calculate_from_changes()
```

Run all tests to ensure nothing broke:
```bash
pytest tests/unit -v
# Expected: ALL PASSED
```

### ❌ TDD Violations (NEVER DO THESE)

- ❌ Write production code before tests
- ❌ Modify tests to pass bad code
- ❌ Skip the Red or Refactor phase
- ❌ Use `pytest.skip` instead of fixing failing tests
- ❌ Write tests after completing a feature

### ✅ TDD Best Practices

- ✅ One test per behavior (AAA pattern: Arrange, Act, Assert)
- ✅ Test names describe expected behavior clearly
- ✅ Use fixtures to reduce duplication
- ✅ Write tests before implementation
- ✅ All tests must pass before commit

---

## 🔄 CI/CD Workflow (MANDATORY)

### ⚠️ 工程纪律强制执行规则

**每次代码修改后，必须执行以下完整检查流程**，任何一项失败都禁止提交代码：

```powershell
# 强制执行脚本（必须执行！）
powershell -ExecutionPolicy Bypass -File scripts/enforce_discipline.ps1

# 或使用 Makefile
make check && make test-unit
```

### Pre-Commit Hooks (Automatic & Mandatory)

**Git 提交前会自动触发以下检查，任何失败都会阻止提交：**

```bash
# 正常提交（自动触发所有检查）
git commit -m "feat: add new feature"

# ⚠️ 禁止！跳过检查会导致严重问题
git commit --no-verify -m "xxx"  # ❌ 严格禁止！
```

**Hooks execute in order** (如果任一步骤失败，后续步骤不会执行):
1. **Ruff Lint** (`ruff --fix`) - 代码规范检查与自动修复
2. **Ruff Format** (`ruff format --check`) - 代码格式检查
3. **Pyright** - 静态类型检查 (0 errors, 0 warnings 才能通过)
4. **Bandit** - 安全漏洞扫描 (No issues 才能通过)
5. **Pytest** - 单元测试 (100% passed 才能通过)
6. **Discipline Check** - 工程纪律完整性最终验证

**If any hook fails, commit is BLOCKED.** 必须修复所有问题后才能提交。

### 质量门禁检查清单

每次代码修改后，**必须手动确认**以下检查清单：

- [ ] **Ruff Lint**: `.venv\Scripts\python -m ruff check jcia tests` → `All checks passed!`
- [ ] **Import Order**: `.venv\Scripts\python -m ruff check --select I jcia tests` → `All checks passed!`
- [ ] **Ruff Format**: `.venv\Scripts\python -m ruff format jcia tests` → `X files formatted`
- [ ] **Type Check**: `.venv\Scripts\python -m pyright jcia tests` → `0 errors, 0 warnings`
- [ ] **Security Scan**: `.venv\Scripts\python -m bandit -r jcia -c pyproject.toml` → `No issues identified.`
- [ ] **Unit Tests**: `.venv\Scripts\python -m pytest tests/unit -v` → `X passed, 0 failed`

### CI Pipeline (GitHub Actions)

When code is pushed to `main` or `develop`:

```yaml
# .github/workflows/ci.yml (auto-executed)
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

**CI Jobs**:
1. **Lint Check** - `make lint`
2. **Type Check** - `pyright jcia tests`
3. **Security Scan** - `make security`
4. **Unit Tests** - `make test-unit` (coverage ≥ 80%)
5. **Integration Tests** - `make test-integration`

**CI will block merge if**:
- Any test fails
- Coverage drops below 80%
- Type errors detected
- Security vulnerabilities found
- Lint errors present

### Quality Gate Check (Before Development)

Before starting development, ensure environment passes quality checks:

```bash
make check     # Full quality check (lint + type + security)
make test      # Run all tests with coverage
```

---

## Build & Test Commands

### ⚡ 快捷命令 (推荐使用)

在 VS Code 终端中，使用以下斜杠命令快速执行：

```powershell
/check       # 运行工程纪律完整检查 (6项) - 推荐！
/lint        # 代码规范检查 (Ruff)
/format      # 代码格式化 (Ruff)
/typecheck   # 类型检查 (Pyright)
/security    # 安全扫描 (Bandit)
/test        # 运行单元测试 (Pytest)
/test-cov    # 带覆盖率的测试
/all         # 运行所有检查
/clean       # 清理构建产物
```

**快捷键**:
- `Ctrl+Shift+A` - 运行 `/check` (工程纪律完整检查)
- `Ctrl+Shift+B` - 显示任务面板

详细使用指南：[QUICK_COMMANDS.md](mdc:.codebuddy/QUICK_COMMANDS.md)

### Setup (Virtual Environment Required)
```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"  # Install with dev dependencies
```

### Testing (PowerShell)
```powershell
# Run unit tests
python -m pytest tests/unit -v

# With coverage
python -m pytest tests/unit -v --cov=jcia

# Run specific test
python -m pytest tests/unit/core/test_change_set.py::TestChangeSet::test_changed_files -v

# Run specific test file
python -m pytest tests/unit/core/test_change_set.py -v
```

### Testing via Makefile
```bash
make test             # Run all tests with coverage (80% minimum)
make test-unit        # Run unit tests only
make test-integration # Run integration tests only
```

### Code Quality
```bash
make lint       # Run ruff linter (includes import sorting)
make format     # Format code with ruff format
make check      # Full check: lint + type check + security
make security   # Run bandit security scan
make clean      # Clean build artifacts
```

### Type Checking
```bash
pyright jcia tests              # Type check (strict mode)
mypy jcia --strict             # Alternative type checker
```

---

## Code Style Guidelines

### General Rules
- **Line length**: 100 characters
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Trailing commas**: Required (skip-magic-trailing-comma = false)
- **Type annotations**: Required (strict mode)

### Import Ordering
```python
# Standard library
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

# Third-party
from pydantic import BaseModel

# Local imports
from jcia.core.entities.change_set import ChangeSet
```

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `ChangeAnalyzer`, `ImpactGraph`)
- **Functions/Methods**: `snake_case` (e.g., `analyze_commits`, `get_upstream_impact`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_DEPTH`)
- **Private members**: `_leading_underscore` (e.g., `_internal_method`)
- **Enums**: `PascalCase` with lowercase values (e.g., `ChangeType.ADD = "add"`)

### Type Hints
```python
from typing import List, Optional, Dict, Set, TYPE_CHECKING
from dataclasses import dataclass, field

def analyze_commits(
    self,
    from_commit: str,
    to_commit: str | None = None  # Python 3.10+ syntax
) -> ChangeSet:
    ...

@dataclass
class MethodChange:
    class_name: str
    method_name: str
    signature: str | None = None
    method_changes: List[MethodChange] = field(default_factory=list)
```

### TYPE_CHECKING for Forward References
Use `TYPE_CHECKING` to avoid circular imports in interfaces. Always use string quotes for forward types:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jcia.core.entities.test_run import TestRun

class TestRunRepository(ABC):
    @abstractmethod
    def save(self, test_run: "TestRun") -> int:
        pass
```

### Error Handling
```python
# Use descriptive exception types
class AnalysisError(Exception):
    """分析过程错误."""
    pass

# Never use bare except or empty catch blocks
try:
    result = self.analyzer.analyze_commits(from_commit)
except GitError as e:
    logger.error(f"Git operation failed: {e}")
    raise
```

### Docstring Format (Google Style)
```python
class ChangeAnalyzer(ABC):
    """变更分析器抽象接口.

    负责检测Git仓库中的代码变更，识别变更的文件和方法。

    Example:
        ```python
        analyzer = PyDrillerAdapter(repo_path)
        changes = analyzer.analyze_commits("abc123", "def456")
        ```
    """

    def analyze_commits(
        self,
        from_commit: str,
        to_commit: Optional[str] = None
    ) -> ChangeSet:
        """分析指定提交范围的变更.

        Args:
            from_commit: 起始提交哈希
            to_commit: 结束提交哈希（默认为HEAD）

        Returns:
            ChangeSet: 变更集合，包含所有变更的文件和方法

        Raises:
            AnalysisError: 分析过程中发生错误
            GitError: Git操作失败
    """
```

---

## Architecture Patterns

### Clean Architecture Layers
```
jcia/
├── core/
│   ├── entities/       # Domain entities (dataclasses, enums)
│   ├── interfaces/     # Abstract interfaces (ABC)
│   ├── services/       # Domain services
│   └── use_cases/      # Application use cases
├── adapters/          # Infrastructure adapters (external systems)
├── infrastructure/    # Infrastructure implementations
└── reports/          # Reporting logic
```

### Dependency Rule (CRITICAL)

**All dependencies must point INWARD toward the core**:

```
❌ WRONG: core/entities → adapters/git
✅ RIGHT: adapters/git → core/entities
```

**Layer Responsibilities**:

1. **Entities** - Pure domain model, no external dependencies
2. **Interfaces** - Abstract definitions for dependencies
3. **Services** - Domain logic not fitting in entities
4. **Use Cases** - Application orchestration
5. **Infrastructure** - Implements interfaces (repositories, config)
6. **Adapters** - Bridge external systems to domain

### Domain Entities
- Use `@dataclass` for entity classes
- Use enums for type-safe constants
- Include properties for computed values
- Provide `to_dict()` for serialization

```python
@dataclass
class FileChange:
    file_path: str
    change_type: ChangeType = ChangeType.MODIFY

    @property
    def is_java_file(self) -> bool:
        return self.file_path.endswith(".java")
```

**Important**: Entity classes starting with "Test" (e.g., `TestStatus`, `TestResult`, `TestRun`, `TestDiff`, `TestComparison`) must include `__test__ = False` to prevent pytest from collecting them as test classes:
```python
@dataclass
class TestResult:
    """单个测试结果."""
    __test__ = False  # Prevent pytest collection
    status: TestStatus = TestStatus.PENDING
```

### Interfaces & Dependency Inversion
- Define abstract interfaces with `@abstractmethod`
- High-level modules depend on abstractions, not concrete implementations
- Adapters implement interfaces to bridge external systems

```python
class ChangeAnalyzer(ABC):
    @abstractmethod
    def analyze_commits(self, from_commit: str) -> ChangeSet:
        pass
```

---

## Testing Guidelines

### Test Structure
```
tests/
├── unit/
│   ├── core/
│   │   ├── test_change_set.py
│   │   └── test_impact_graph.py
│   └── adapters/
└── integration/
```

### Test Naming
- Test classes: `Test{ClassName}` (e.g., `TestChangeSet`)
- Test methods: `test_{method_name}` (e.g., `test_is_java_file`)
- Use descriptive names that explain behavior

### Test Patterns (AAA: Arrange-Act-Assert)
```python
class TestChangeSet:
    """ChangeSet测试类."""

    def test_changed_files(self) -> None:
        """测试变更文件列表."""
        # Arrange
        change_set = ChangeSet(
            file_changes=[
                FileChange(file_path="File1.java"),
                FileChange(file_path="File2.java"),
            ]
        )

        # Act
        result = change_set.changed_files

        # Assert
        assert result == ["File1.java", "File2.java"]

    def test_empty_change_set(self) -> None:
        """测试空变更集判断."""
        # Arrange
        empty_set = ChangeSet()

        # Act & Assert
        assert empty_set.is_empty() is True
```

### Test Markers
```python
@pytest.mark.unit
def test_something() -> None:
    ...

@pytest.mark.integration
@pytest.mark.slow
def test_something_slow() -> None:
    ...
```

### Coverage Requirements
- **Overall**: ≥ 80%
- **Entities**: ≥ 95%
- **Services**: ≥ 85%
- **Adapters**: ≥ 75%
- **Interfaces**: N/A (excluded from coverage)

**Note**: Interface layer (`jcia/core/interfaces/*`) is excluded from coverage requirements because it contains only abstract methods with no implementation.

---

## Pre-commit Hooks

The project uses pre-commit hooks for automatic quality checks:
1. **ruff**: Auto-fix linting issues
2. **ruff-format**: Format code
3. **pyright**: Type checking
4. **bandit**: Security scanning
5. **pytest-check**: Run unit tests before commit

Hooks run automatically on staged files before commit.

---

## Common Pitfalls

### ❌ 严格禁止 (会导致工程纪律失败)
- **跳过质量检查**: 使用 `git commit --no-verify` 绕过 pre-commit hooks ❌
- **选择性检查**: 只运行部分检查，跳过其他检查 ❌
- **提交未测试代码**: 任何代码提交前必须通过完整测试 ❌
- **忽略类型错误**: 滥用 `# type: ignore` 抑制类型检查 ❌
- **降低覆盖率**: 新增代码必须保持 80%+ 覆盖率 ❌
- **使用 `any` 类型**: 无正当理由使用 `any` 而不是 `Any` ❌
- **使用 bare `except:`**: 捕获所有异常但不处理 ❌
- **在测试文件中用通配符导入**: `from jcia.core.*` ❌
- **使用 print 语句**: 应该使用 logging ❌
- **忘记 `__test__ = False`**: "Test*" 实体类必须设置 ❌
- **先写代码后写测试**: 违反 TDD 红-绿-重构流程 ❌

### ✅ 必须执行 (工程纪律要求)
- **完整质量检查**: 每次修改后执行 `scripts/enforce_discipline.ps1` ✅
- **类型注解**: 使用 Python 3.10+ 语法 `str | None` 而不是 `Optional[str]` ✅
- **前向引用**: 使用 `TYPE_CHECKING` 避免循环导入 ✅
- **数据类**: 使用 dataclasses 存储简单数据 ✅
- **目录结构**: 遵循现有目录结构 ✅
- **TDD 流程**: 红-绿-重构，先写测试再实现 ✅
- **Google 风格 Docstring**: 统一文档格式 ✅
- **PowerShell 测试**: 在 PowerShell 中运行测试，虚拟环境激活 ✅
- **字符串引用**: 接口注解中使用字符串引用前向类型 ✅
- **提交前检查**: 所有测试通过 + 完整质量检查 ✅

### 工程纪律执行要点

**每次任务结束前必须执行：**
1. 运行 `scripts/enforce_discipline.ps1`
2. 确认所有检查通过
3. 如检查失败，修复问题后重新运行全部检查
4. 严禁使用 `--no-verify` 跳过检查

---

## Configuration Files Reference

- **pyproject.toml**: Build config, dependencies, ruff/pyright/pytest/bandit/mypy settings, coverage exclusions
- **Makefile**: Build, test, and quality commands
- **.pre-commit-config.yaml**: Pre-commit hook definitions
- **.jcia.yaml.example**: Runtime configuration template (copy to .jcia.yaml)
- **PROJECT_CONSTITUTION.md**: Project constitution (TDD, CI/CD, architecture rules) - MANDATORY READING

**Critical**: Coverage threshold is set to 80% in `[tool.pytest.ini_options]`. Interface layer (`jcia/core/interfaces/*`) is excluded from coverage calculation as it contains only abstract methods.

---

## External Dependencies

Key external libraries:
- **pydriller**: Git commit analysis
- **pyyaml**: Configuration parsing
- **click**: CLI framework
- **pydantic**: Data validation
- **rich**: Terminal output formatting
- **requests/beautifulsoup4**: HTTP & HTML parsing

---

## Next Steps for Development

1. **Read PROJECT_CONSTITUTION.md** (MANDATORY)
2. Review `plan.md` to understand project roadmap
3. Check current progress: Phase 4/13 completed
4. Start with Phase 5: Adapters Layer Implementation
5. Follow TDD: Write test → Implement → Refactor
6. Ensure `make check` and `make test` pass before committing

---

## Quick Reference

```bash
# Full quality check before development
make check && make test

# TDD workflow for new feature
# 1. Write failing test
pytest tests/.../test_new_feature.py -v  # Should FAIL
# 2. Implement minimum code
# 3. Run test again
pytest tests/.../test_new_feature.py -v  # Should PASS
# 4. Refactor while tests pass
# 5. Run all tests
pytest tests/unit -v  # All should PASS

# Pre-commit hooks run automatically with:
git commit -m "feat: add new feature"
```
