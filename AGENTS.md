# JCIA - Agent Configuration Guide

Guide for agentic coding agents working with JCIA (Java Code Impact Analyzer).

**Project**: Python 3.10+ clean architecture tool for analyzing Java code change impact.

---

## Build & Test Commands

**Setup** (run once):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
make setup-hooks  # Configure pre-commit hooks
```

**Testing**:
```powershell
pytest tests/unit -v                                          # All unit tests
pytest tests/unit -v --cov=jcia                              # With coverage
pytest tests/unit/core/test_change_set.py -v                 # Specific test file
pytest tests/unit/core/test_change_set.py::TestChangeSet::test_changed_files -v  # Specific test
```

**Quality Checks**:
```powershell
make lint          # Ruff linter (includes import sorting)
make format        # Format with ruff format
make check         # Full check: lint + type + security
make security      # Bandit security scan
pyright jcia tests # Type checking
```

**Makefile Targets**: `test`, `test-unit`, `test-integration`, `lint`, `format`, `check`, `security`, `clean`, `setup-hooks`

---

## Code Style Guidelines

**General**: Line length 100, 4-space indent, double quotes, trailing commas required

**Import ordering**: Standard library → Third-party → Local imports

**Naming**: Classes `PascalCase`, functions/methods `snake_case`, constants `UPPER_SNAKE_CASE`, private members `_leading_underscore`, enums `PascalCase` with lowercase values

**Type hints** (Python 3.10+ syntax): Use `str | None` not `Optional[str]`, use `TYPE_CHECKING` for circular imports

**Forward references**:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from jcia.core.entities.test_run import TestRun
```

**Docstrings**: Google style convention (configured in pyproject.toml)

**Error handling**: Use descriptive exceptions, never bare `except:`, always log errors, re-raise with context

**Entities**: Use `@dataclass`, add `__test__ = False` for classes starting with "Test" to prevent pytest collection

---

## Architecture Patterns

**Clean Architecture** (dependencies point INWARD):
- `jcia/core/entities/` - Domain entities (dataclasses, enums)
- `jcia/core/interfaces/` - Abstract interfaces (ABC)
- `jcia/core/services/` - Domain services
- `jcia/core/use_cases/` - Application use cases
- `jcia/adapters/` - Infrastructure adapters
- `jcia/infrastructure/` - Infrastructure implementations
- `jcia/reports/` - Reporting logic

**Dependency Rule**: Adapters → Infrastructure → Use Cases → Services → Entities

---

## Testing Guidelines

**Test structure**: Classes `Test{ClassName}`, methods `test_{method_name}`, use AAA pattern (Arrange-Act-Assert)

**Coverage**: ≥80% overall, ≥95% entities, ≥85% services, ≥75% adapters (interfaces excluded)

**TDD Workflow**: Red (write failing test) → Green (implement) → Refactor

---

## Critical Rules

**Pre-commit hooks** (run automatically, block commit on failure):
1. Ruff lint (`--fix`)
2. Ruff format (`--check`)
3. Pyright type checking
4. Bandit security scan
5. Pytest unit tests
6. Discipline enforcement

**NEVER**: Skip hooks with `--no-verify`, use `# type: ignore` without justification, use bare `except:`, use `any` instead of `Any`, write production code before tests, commit failing tests

**ALWAYS**: Follow TDD cycle, use Python 3.10+ type syntax (`str | None`), use `TYPE_CHECKING` for forward references, use `@dataclass` for data structures, use Google-style docstrings, ensure all tests pass before commit

---

## Configuration Files

- `pyproject.toml`: Build config, dependencies, Ruff/Pyright/Bandit settings
- `Makefile`: Build/test commands
- `.pre-commit-config.yaml`: Pre-commit hooks configuration
- `PROJECT_CONSTITUTION.md`: Detailed rules (TDD, CI/CD, architecture, Git workflow)

**For detailed architecture, TDD process, CI/CD workflow, and Git conventions → See PROJECT_CONSTITUTION.md (718 lines comprehensive guide)**
