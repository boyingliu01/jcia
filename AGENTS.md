# JCIA - Agent Configuration Guide

This guide helps agentic coding agents work effectively with JCIA (Java Code Impact Analyzer).

## Project Overview

JCIA is a Python tool for analyzing Java code change impact. Uses clean architecture with Python 3.10+, virtual environment (`.venv`), and requires PowerShell for testing.

**Current Progress**: Phase 4/13 completed - Domain Entities & Core Interfaces

---

## Build & Test Commands

**Setup** (run once):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

**Testing** (PowerShell):
```powershell
# Run all unit tests
python -m pytest tests/unit -v

# Run with coverage
python -m pytest tests/unit -v --cov=jcia

# Run specific test
python -m pytest tests/unit/core/test_change_set.py::TestChangeSet::test_changed_files -v

# Run specific test file
python -m pytest tests/unit/core/test_change_set.py -v
```

**Makefile targets** (alternative):
```powershell
make test          # All tests with coverage
make test-unit     # Unit tests only
make lint          # Ruff linter (includes import sorting)
make format        # Format code with ruff format
make check         # Full check: lint + type + security
make security      # Bandit security scan
make clean         # Clean build artifacts
```

**Type checking**:
```powershell
pyright jcia tests              # Type check
mypy jcia --strict             # Alternative
```

---

## Code Style Guidelines

**General**: Line length 100, 4-space indent, double quotes, required trailing commas

**Import ordering**:
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

**Naming conventions**:
- Classes: `PascalCase` (e.g., `ChangeAnalyzer`, `ImpactGraph`)
- Functions/Methods: `snake_case` (e.g., `analyze_commits`, `get_upstream_impact`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_DEPTH`)
- Private members: `_leading_underscore`
- Enums: `PascalCase` with lowercase values (e.g., `ChangeType.ADD = "add"`)

**Type hints** (Python 3.10+ syntax):
```python
def analyze_commits(
    self,
    from_commit: str,
    to_commit: str | None = None  # Use | not Optional[]
) -> ChangeSet:
    ...

@dataclass
class MethodChange:
    class_name: str
    method_name: str
    signature: str | None = None
    method_changes: List[MethodChange] = field(default_factory=list)
```

**Forward references** (use TYPE_CHECKING for circular imports):
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jcia.core.entities.test_run import TestRun

class TestRunRepository(ABC):
    @abstractmethod
    def save(self, test_run: "TestRun") -> int:
        pass
```

**Error handling**:
```python
# Use descriptive exceptions, never bare except
try:
    result = self.analyzer.analyze_commits(from_commit)
except GitError as e:
    logger.error(f"Git operation failed: {e}")
    raise
```

**Docstrings** (Google style):
```python
class ChangeAnalyzer(ABC):
    """变更分析器抽象接口.

    负责检测Git仓库中的代码变更，识别变更的文件和方法。
    """

    def analyze_commits(
        self,
        from_commit: str,
        to_commit: str | None = None
    ) -> ChangeSet:
        """分析指定提交范围的变更.

        Args:
            from_commit: 起始提交哈希
            to_commit: 结束提交哈希（默认为HEAD）

        Returns:
            ChangeSet: 变更集合

        Raises:
            AnalysisError: 分析过程中发生错误
        """
```

---

## Architecture Patterns

**Clean Architecture layers** (dependencies point INWARD):
```
jcia/
├── core/
│   ├── entities/       # Domain entities (dataclasses, enums)
│   ├── interfaces/     # Abstract interfaces (ABC)
│   ├── services/       # Domain services
│   └── use_cases/      # Application use cases
├── adapters/          # Infrastructure adapters
├── infrastructure/    # Infrastructure implementations
└── reports/          # Reporting logic
```

**Entities**: Use `@dataclass`, include properties, provide `to_dict()` for serialization

**Important**: Entity classes starting with "Test" must include `__test__ = False`:
```python
@dataclass
class TestResult:
    """单个测试结果."""
    __test__ = False  # Prevent pytest collection
    status: TestStatus = TestStatus.PENDING
```

---

## Testing Guidelines

**Test structure**:
- Test classes: `Test{ClassName}`
- Test methods: `test_{method_name}`
- Use AAA pattern: Arrange, Act, Assert
- Descriptive names that explain behavior

**Test example**:
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
```

**Coverage**: ≥80% overall. Interface layer excluded (no implementation).

---

## Critical Rules

**Pre-commit hooks** (run automatically, block commit on failure):
1. Ruff lint (`--fix`)
2. Ruff format (`--check`)
3. Pyright type checking
4. Bandit security scan
5. Pytest unit tests
6. Discipline enforcement

**NEVER**:
- Skip pre-commit hooks with `--no-verify`
- Use `# type: ignore` without justification
- Use bare `except:` or empty catch blocks
- Use `any` instead of `Any` type
- Write production code before tests (TDD violation)
- Commit failing tests

**ALWAYS**:
- Follow TDD: Red (write failing test) → Green (implement) → Refactor
- Use Python 3.10+ type syntax: `str | None` not `Optional[str]`
- Use `TYPE_CHECKING` for forward references
- Use `@dataclass` for simple data structures
- Use Google-style docstrings
- All tests pass before commit

---

## Quick Reference

```powershell
# Full quality check before development
make check && make test

# TDD workflow
# 1. Write failing test (should FAIL)
pytest tests/.../test_new_feature.py -v
# 2. Implement minimum code
# 3. Run test again (should PASS)
pytest tests/.../test_new_feature.py -v
# 4. Refactor while tests pass
# 5. Run all tests (all PASS)
pytest tests/unit -v

# Pre-commit hooks run automatically with commit
git commit -m "feat: add new feature"
```

**Configuration files**:
- `pyproject.toml`: Build config, dependencies, tool settings
- `Makefile`: Build/test commands
- `.pre-commit-config.yaml`: Pre-commit hooks
- `PROJECT_CONSTITUTION.md`: Detailed rules (TDD, CI/CD, architecture)
