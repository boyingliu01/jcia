# JCIA - Agent Configuration Guide

Guide for agentic coding agents working with JCIA (Java Code Impact Analyzer).

**Project**: Python 3.10+ clean architecture tool for analyzing Java code change impact and intelligent test selection.

**Version**: 0.1.0
**License**: MIT
**Language**: Python (3.10, 3.11, 3.12)

---

## Project Overview

JCIA (Java Code Impact Analyzer) is a development tool that helps teams quickly identify the scope of code changes, intelligently select test cases that need to be run, and provide regression analysis capabilities.

**Core Features**:
- 🔍 **Change Impact Analysis** - Automatically analyze Git commits to identify changed files and methods
- 📊 **Impact Graph Construction** - Build call chain graphs and calculate affected classes and methods
- 🎯 **Intelligent Test Selection** - Select test cases based on STARTS algorithm and impact scope
- 🤖 **AI Test Generation** - Integrated LLM services (Volcengine, OpenAI) for automatic test case generation suggestions
- 🚀 **APM-Based Recommendations** - SkyWalking APM integration for test recommendations and performance analysis
- 🧪 **Test Execution** - Maven Surefire integration for selective test execution and coverage collection
- 📈 **Multi-format Reports** - Support HTML, JSON, Markdown format reports
- 🔄 **Regression Analysis** - Compare baseline and regression test results to identify regression issues

**Performance Targets**:
- Single commit analysis: < 10 seconds
- Impact graph construction: < 5 seconds
- Test selection: < 3 seconds
- Support for 1000+ test cases
- Selective test acceleration: ≥ 50%

**Test Project**:
- **Jenkins** (`jenkins-full/`) - Open-source continuous integration server used for validation and testing of JCIA functionality. This is a real Java project with ~1000+ test cases that serves as the primary testbed for impact analysis and test selection features.

---

## Build & Test Commands

### Environment Setup (run once)

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment (PowerShell)
.venv\Scripts\Activate.ps1

# Install development dependencies
pip install -e ".[dev]"

# Configure pre-commit hooks
make setup-hooks
```

### Testing

```powershell
# Run all tests
make test

# Run unit tests only
pytest tests/unit -v

# Run integration tests only
pytest tests/integration -v

# Run tests with coverage
pytest tests/unit -v --cov=jcia --cov-report=term-missing

# Run specific test file
pytest tests/unit/core/test_change_set.py -v

# Run specific test method
pytest tests/unit/core/test_change_set.py::TestChangeSet::test_changed_files -v

# Run with coverage report (HTML)
pytest tests/unit --cov=jcia --cov-report=html --cov-report=term-missing
```

### Code Quality Checks

```powershell
# Lint check (Ruff)
make lint

# Format code
make format

# Full check (lint + type + security)
make check

# Security scan (Bandit)
make security

# Type checking (Pyright)
pyright jcia tests
```

### Makefile Targets

- `help` - Display available targets with descriptions
- `venv` - Create Python virtual environment in `.venv/`
- `install` - Install production dependencies from requirements.txt
- `install-dev` - Install development dependencies (includes testing tools)
- `setup-hooks` - Configure pre-commit hooks for quality enforcement
- `test` - Run all tests with coverage report
- `test-unit` - Run unit tests only (tests/unit/)
- `test-integration` - Run integration tests only (tests/integration/)
- `lint` - Run Ruff linter with import sorting
- `format` - Format code using Ruff formatter
- `check` - Run all quality checks (lint + type + security)
- `security` - Run Bandit security vulnerability scanner
- `clean` - Clean all build artifacts, cache files, and temporary directories

---

## Project Structure

```
jcia/
├── adapters/              # Infrastructure adapters (external system bridges)
│   ├── ai/               # AI/LLM service adapters
│   │   ├── llm_adapter.py
│   │   ├── volcengine_adapter.py
│   │   ├── openai_adapter.py
│   │   └── skywalking_adapter.py
│   ├── database/         # Database adapters
│   │   └── sqlite_adapter.py
│   ├── git/              # Git repository adapters
│   │   └── pydriller_adapter.py
│   ├── maven/            # Maven build system adapters
│   │   └── maven_adapter.py
│   ├── test_runners/     # Test execution adapters
│   │   └── maven_surefire_test_executor.py
│   └── tools/            # External tool adapters
│       ├── mock_call_chain_analyzer.py
│       ├── starts_test_selector_adapter.py
│       ├── java_all_call_graph_adapter.py
│       └── skywalking_call_chain_adapter.py
├── cli/                  # Command-line interface
│   └── main.py
├── core/                 # Core business logic (clean architecture)
│   ├── entities/         # Domain entities (dataclasses, enums)
│   │   ├── change_set.py
│   │   ├── impact_graph.py
│   │   ├── test_case.py
│   │   └── test_run.py
│   ├── interfaces/       # Abstract interfaces (ABC)
│   │   ├── analyzer.py
│   │   ├── ai_service.py
│   │   ├── call_chain_analyzer.py
│   │   ├── file_system.py
│   │   ├── repository.py
│   │   ├── test_runner.py
│   │   └── tool_wrapper.py
│   ├── services/         # Domain services
│   │   ├── impact_analysis_service.py
│   │   ├── call_chain_builder.py
│   │   ├── test_selection_service.py
│   │   ├── test_generator_service.py
│   │   └── change_comparison_service.py
│   └── use_cases/        # Application use cases
│       ├── analyze_impact.py
│       ├── generate_tests.py
│       ├── generate_report.py
│       └── run_regression.py
├── infrastructure/       # Infrastructure implementations
│   ├── config/           # Configuration management
│   │   └── config_manager.py
│   ├── database/         # Database repositories
│   │   ├── sqlite_adapter.py
│   │   └── sqlite_repository.py
│   ├── fs/               # File system operations
│   │   └── file_system.py
│   └── logging/          # Logging infrastructure
│       └── logger.py
└── reports/              # Reporting logic
    ├── base.py
    ├── html_reporter.py
    ├── json_reporter.py
    ├── markdown_reporter.py
    └── templates/

tests/
├── unit/                 # Unit tests
│   ├── core/             # Tests for core business logic
│   ├── adapters/         # Tests for adapter implementations
│   ├── infrastructure/   # Tests for infrastructure components
│   ├── services/         # Tests for domain services
│   ├── use_cases/        # Tests for application use cases
│   └── cli/              # Tests for CLI commands
├── integration/          # Integration tests
│   └── adapters/         # Integration tests with external systems
├── fixtures/             # Shared test fixtures
├── test_data/            # Sample data for testing
└── conftest_base.py      # Base pytest configuration

scripts/                  # Development and utility scripts
├── check_tdd_compliance.ps1
├── enforce_discipline.ps1
├── run_pytest.ps1
└── setup_env.ps1

jenkins-full/            # Jenkins CI/CD project (testbed for JCIA)
├── core/                # Core Java classes
├── test/                # Java test classes (1000+ tests)
├── pom.xml              # Maven build configuration
└── Jenkinsfile          # Jenkins pipeline configuration

dev-workflow/            # Development workflow automation scripts
docs/                    # Additional documentation
report/                  # Generated reports
review/                  # Code review reports
research/                # Research documents
```

**Root Configuration Files:**
- `pyproject.toml` - Python project configuration, dependencies, and tool settings
- `Makefile` - Build automation commands
- `pytest.ini` - Pytest configuration with test markers
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `jcia.yaml` - Runtime configuration (optional)
- `.jcia.yaml.example` - Example configuration file
- `AGENTS.md` - This file (agent configuration guide)
- `PROJECT_CONSTITUTION.md` - Comprehensive project rules and guidelines
- `README.md` - Project overview and quick start guide

---

## Architecture Patterns

### Clean Architecture

JCIA strictly follows Clean Architecture principles with dependencies pointing INWARD:

```
Adapters Layer (Git, Maven, AI, Database)
    ↓
Infrastructure Layer (Repositories, Config, Logging)
    ↓
Use Cases Layer (Business Orchestration)
    ↓
Services Layer (Domain Logic)
    ↓
Entities Layer (Domain Models)
```

**Dependency Rule**: Adapters → Infrastructure → Use Cases → Services → Entities

### Layer Responsibilities

1. **Entities Layer** (`jcia/core/entities/`)
   - Pure business logic and data models
   - No external dependencies
   - Use `@dataclass` for entity definitions

2. **Interfaces Layer** (`jcia/core/interfaces/`)
   - Abstract interfaces using `ABC` and `@abstractmethod`
   - Define contracts for external system interactions

3. **Services Layer** (`jcia/core/services/`)
   - Domain business logic
   - Coordinate multiple entities
   - No dependency on Adapters or Infrastructure

4. **Use Cases Layer** (`jcia/core/use_cases/`)
   - Application business orchestration
   - Define transaction boundaries
   - Depend on interfaces, not implementations

5. **Infrastructure Layer** (`jcia/infrastructure/`)
   - Implement core layer interfaces
   - Handle data persistence, configuration, logging
   - No dependency on Adapters

6. **Adapters Layer** (`jcia/adapters/`)
   - Bridge external systems (Git, Maven, AI, Database)
   - Transform external data to domain entities
   - Depend on all internal layers

---

## Code Style Guidelines

### General Rules

- **Line length**: 100 characters
- **Indentation**: 4 spaces
- **Quotes**: Double quotes
- **Trailing commas**: Required for multi-line structures

### Import Ordering

Standard library → Third-party → Local imports

```python
# 1. Standard library
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

# 2. Third-party libraries
from pydantic import BaseModel
from rich.console import Console

# 3. Local imports
from jcia.core.entities.change_set import ChangeSet
from jcia.core.interfaces.analyzer import ChangeAnalyzer
```

### Naming Conventions

| Type | Format | Example |
|------|--------|---------|
| Classes | `PascalCase` | `ChangeAnalyzer`, `ImpactGraph` |
| Functions/Methods | `snake_case` | `analyze_commits`, `get_upstream_impact` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_DEPTH`, `DEFAULT_TIMEOUT` |
| Private Members | `_leading_underscore` | `_internal_method`, `_cache` |
| Enums | `PascalCase` | `ChangeType`, `ImpactSeverity` |
| Enum Values | lowercase | `ChangeType.ADD = "add"` |

### Type Hints (Python 3.10+)

Use modern type syntax: `str | None` instead of `Optional[str]`

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jcia.core.entities.test_run import TestRun

def analyze_commits(
    from_commit: str,
    to_commit: str | None = None
) -> ChangeSet:
    """Analyze commits within the specified range."""
    ...
```

### Docstrings

Use Google style convention (configured in pyproject.toml):

```python
def analyze_commits(
    self,
    from_commit: str,
    to_commit: str | None = None
) -> ChangeSet:
    """Analyze commits within the specified range.

    Args:
        from_commit: Starting commit hash
        to_commit: Ending commit hash (defaults to HEAD)

    Returns:
        ChangeSet: Collection of changes with all changed files and methods

    Raises:
        AnalysisError: If analysis fails
        GitError: If Git operations fail

    Example:
        ```python
        analyzer = PyDrillerAdapter(repo_path)
        changes = analyzer.analyze_commits("abc123", "def456")
        ```
    """
```

### Error Handling

Use descriptive exceptions, never bare `except:`, always log errors:

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = self.analyzer.analyze_commits(from_commit)
except GitError as e:
    logger.error(f"Git operation failed: {e}")
    raise AnalysisError(f"Failed to analyze commits: {e}") from e
```

### Entities

Use `@dataclass` for data structures. Add `__test__ = False` for classes starting with "Test" to prevent pytest collection:

```python
from dataclasses import dataclass

@dataclass
class ChangeSet:
    """Represents a set of code changes."""
    file_changes: list[FileChange]
    commit_hash: str
    __test__ = False  # Prevent pytest collection
```

---

## Testing Guidelines

### Test Structure

- **Test classes**: `Test{ClassName}`
- **Test methods**: `test_{method_name}_{scenario}`
- **Pattern**: AAA (Arrange-Act-Assert)

```python
def test_add_file_change_increases_count(self) -> None:
    # Arrange (准备)
    change_set = ChangeSet()
    file_change = FileChange(file_path="Service.java")

    # Act (执行)
    change_set.add_file_change(file_change)

    # Assert (断言)
    assert len(change_set.file_changes) == 1
```

### Test Coverage Requirements

- **Overall coverage**: ≥ 80%
- **Entities layer**: ≥ 95%
- **Services layer**: ≥ 85%
- **Adapters layer**: ≥ 75%
- **Interfaces layer**: Not required (only abstract methods)

### Test Markers

```python
@pytest.mark.unit
def test_unit_behavior() -> None:
    ...

@pytest.mark.integration
@pytest.mark.slow
def test_integration_test() -> None:
    ...
```

### TDD Workflow

**Red → Green → Refactor**

1. **Write failing test** (Red)
2. **Implement minimal code** (Green)
3. **Refactor while tests pass** (Refactor)

### Test Execution Strategies

JCIA supports multiple test execution strategies:

- **ALL**: Execute all test cases
- **STARTS**: Use STARTS algorithm for selective test execution
- **IMPACT_BASED**: Execute tests based on impact analysis results
- **HYBRID**: Combine multiple strategies for optimal test selection

**NEVER**:
- Write production code before tests
- Modify test logic to make tests pass
- Skip TDD cycle phases
- Use `pytest.skip` instead of fixing failures

**ALWAYS**:
- New features must have tests first
- All tests must pass before commit
- Refactor only with sufficient test coverage
- Use fixtures to reduce duplication

---

## Critical Rules

### Pre-commit Hooks

Pre-commit hooks run automatically and **block commit on failure**:

1. **Ruff lint** (v0.1.9, `--fix`) - Auto-fix lint issues and code style violations
2. **Ruff format** (v0.1.9, `--check`) - Check code formatting compliance
3. **Pyright type checking** (v1.1.340) - Strict mode type validation
4. **Bandit security scan** (v1.7.6) - Security vulnerability detection with Toml config
5. **Pytest unit tests** - Run all unit tests with short traceback
6. **Discipline enforcement** - Verify development practices via PowerShell script

**Configuration file**: `.pre-commit-config.yaml`
**Enforcement script**: `scripts/enforce_discipline.ps1`

### NEVER

- Skip hooks with `--no-verify`
- Use `# type: ignore` without justification
- Use bare `except:` clauses
- Use `any` instead of `Any`
- Write production code before tests
- Commit failing tests
- Hardcode secrets or API keys

### ALWAYS

- Follow TDD cycle (Red → Green → Refactor)
- Use Python 3.10+ type syntax (`str | None`)
- Use `TYPE_CHECKING` for forward references
- Use `@dataclass` for data structures
- Use Google-style docstrings
- Ensure all tests pass before commit
- Use environment variables for sensitive data

---

## Configuration Files

### Primary Configuration

- **`pyproject.toml`**: Build config, dependencies, Ruff/Pyright/Bandit settings
- **`Makefile`**: Build and test commands
- **`.pre-commit-config.yaml`**: Pre-commit hooks configuration
- **`pytest.ini`**: Pytest configuration with test markers
- **`jcia.yaml`**: Runtime configuration (optional)

### Configuration File Details

#### pyproject.toml

Contains all project metadata, dependencies, and tool configurations:

- **Build system**: setuptools
- **Python versions**: 3.10, 3.11, 3.12
- **Dependencies**: click, pydriller, pyyaml, jinja2, requests, beautifulsoup4, rich, pydantic, defusedxml
- **Dev dependencies**: pytest, ruff, pyright, bandit, pre-commit, mypy
- **Ruff**: Line length 100, Google docstring convention
- **Pyright**: Basic mode, venv detection
- **Coverage**: ≥ 80% requirement, interface exclusions

#### pytest.ini

- Test paths: `tests/`
- Test file patterns: `test_*.py`, `*_test.py`
- Test class patterns: `Test*`
- Test function patterns: `test_*`
- Markers: `unit`, `integration`, `slow`

#### jcia.yaml (Runtime Configuration)

Optional configuration file for JCIA behavior:

```yaml
repository:
  path: /path/to/your/java/project

analyzer:
  max_depth: 10
  include_test_files: false

report:
  format: html
  output_dir: ./reports

ai:
  provider: volcengine
  model: gpt-4
```

#### Environment Variables

**Volcengine AI Service:**
- `VOLCENGINE_ACCESS_KEY` - Volcengine access key
- `VOLCENGINE_SECRET_KEY` - Volcengine secret key
- `VOLCENGINE_APP_ID` - Volcengine application ID

**OpenAI Service:**
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_BASE_URL` - OpenAI API base URL (optional, defaults to https://api.openai.com/v1)
- `OPENAI_MODEL` - OpenAI model name (optional, defaults to gpt-4-turbo-preview)

**SkyWalking APM:**
- `SKYWALKING_OAP_SERVER` - SkyWalking OAP server address (optional, defaults to http://localhost:12800)
- `SKYWALKING_API_TOKEN` - SkyWalking API token (optional)

---

## Development Tools and Scripts

### Available Scripts

Located in `scripts/` directory:

- **`check_tdd_compliance.ps1`** - Verify TDD compliance
- **`enforce_discipline.ps1`** - Enforce development discipline rules (runs 6 quality gates)
- **`run_pytest.ps1`** - Run pytest with specific configurations
- **`setup_env.ps1`** - Setup development environment

**Quality Gates in enforce_discipline.ps1:**
1. Ruff Lint - Code style and quality checks
2. Ruff Import Sorting - Import ordering validation
3. Ruff Format - Code formatting verification
4. Pyright Type Checking - Static type validation
5. Bandit Security Scan - Security vulnerability detection
6. Pytest Unit Tests - All unit tests must pass

### CLI Commands

JCIA provides a command-line interface (`jcia` command):

```bash
# Analyze change impact
jcia analyze --repo-path /path/to/repo --from-commit abc123 --to-commit def456

# Generate test cases
jcia test --repo-path /path/to/project --target-class com.example.Service

# Execute regression testing
jcia regression --repo-path /path/to/project --baseline-commit abc123 --regression-commit def456

# Generate reports
jcia report --output-dir ./reports --format html

# Configuration management
jcia config --show
jcia config --set project.path=/path/to/project
```

**Available CLI Options:**

**`analyze` Command:**
- `--repo-path`: Git repository path (required)
- `--from-commit`: Starting commit hash
- `--to-commit`: Ending commit hash (defaults to HEAD)
- `--commit-range`: Commit range (e.g., abc123..def456)
- `--max-depth`: Maximum trace depth (default: 10)

**`test` Command:**
- `--repo-path`: Project path (required)
- `--target-class`: Target class (can be used multiple times)
- `--coverage-file`: Coverage report file path
- `--min-confidence`: Minimum confidence threshold (default: 0.5)

**`regression` Command:**
- `--repo-path`: Project path (required)
- `--baseline-commit`: Baseline commit hash
- `--regression-commit`: Regression commit hash
- `--execute-coverage`: Execute and collect coverage
- `--save-results`: Save test results to database

**`report` Command:**
- `--output-dir`: Output directory (required)
- `--format`: Report format (json/html/markdown/console)
- `--include-details`: Include detailed information

**`config` Command:**
- `--show`: Display current configuration
- `--set KEY=VALUE`: Set configuration value

---

## Dependencies

### Core Dependencies

- **click** (≥8.1.0) - Command-line interface
- **pydriller** (≥2.6.0) - Git repository analysis
- **pyyaml** (≥6.0.1) - YAML configuration parsing
- **jinja2** (≥3.1.2) - Template rendering for reports
- **requests** (≥2.31.0) - HTTP client for API calls
- **beautifulsoup4** (≥4.12.0) - HTML parsing for reports
- **rich** (≥13.7.0) - Rich terminal output
- **pydantic** (≥2.5.0) - Data validation
- **defusedxml** (≥0.7.1) - Safe XML parsing for STARTS and Surefire reports

### Development Dependencies

- **pytest** (≥7.4.0) - Testing framework
- **pytest-cov** (≥4.1.0) - Coverage reporting
- **pytest-mock** (≥3.12.0) - Mocking utilities
- **pytest-asyncio** (≥0.21.0) - Async test support
- **ruff** (≥0.1.0) - Fast Python linter and formatter
- **pyright** (≥1.1.340) - Static type checker
- **bandit** (≥1.7.6) - Security vulnerability scanner
- **pre-commit** (≥3.6.0) - Pre-commit hooks framework
- **mypy** (≥1.7.0) - Static type checker

---

## Integration Adapters

### AI Service Adapters

**Volcengine Adapter** (`jcia/adapters/ai/volcengine_adapter.py`)
- Primary LLM service for test generation
- Requires VOLCENGINE_ACCESS_KEY, VOLCENGINE_SECRET_KEY, VOLCENGINE_APP_ID
- Supports test case generation and code analysis

**OpenAI Adapter** (`jcia/adapters/ai/openai_adapter.py`)
- Alternative LLM service using OpenAI API
- Requires OPENAI_API_KEY
- Supports custom base URL and model configuration
- Default model: gpt-4-turbo-preview

**SkyWalking Adapter** (`jcia/adapters/ai/skywalking_adapter.py`)
- APM-based test recommendations
- Performance bottleneck analysis
- Exception tracking
- Uses SkyWalking OAP Server GraphQL API

### Test Selection & Execution

**STARTS Test Selector** (`jcia/adapters/tools/starts_test_selector_adapter.py`)
- Implements STARTS algorithm for regression test selection
- Analyzes class-level dependencies
- Maps tests to source code
- Reduces test execution time by 50%+
- Uses `starts-maven-plugin` (version 1.4)

**Maven Surefire Executor** (`jcia/adapters/test_runners/maven_surefire_test_executor.py`)
- Executes selected test cases
- Collects JaCoCo coverage data
- Parses test results from Surefire XML reports
- Supports selective test execution

**Java All Call Graph** (`jcia/adapters/tools/java_all_call_graph_adapter.py`)
- Builds call chain graphs
- Analyzes method dependencies
- Supports impact analysis

### Git & Build System

**PyDriller Adapter** (`jcia/adapters/git/pydriller_adapter.py`)
- Parses Git repository history
- Identifies file and method changes
- Extracts commit metadata

**Maven Adapter** (`jcia/adapters/maven/maven_adapter.py`)
- Manages Maven build lifecycle
- Executes Maven commands
- Handles project dependencies

---

## Additional Resources

### Documentation Files

- **`README.md`** - Project overview and quick start guide
- **`CHANGELOG.md`** - Version history and changelog
- **`CONTRIBUTING.md`** - Contribution guidelines
- **`PROJECT_CONSTITUTION.md`** - Comprehensive project rules (718 lines)
  - Detailed TDD process
  - CI/CD workflow
  - Architecture patterns
  - Git workflow conventions
  - Security requirements
  - Performance targets

### Project Constitution Highlights

For detailed information on:
- **TDD Workflow**: Red → Green → Refactor cycle
- **CI/CD Pipeline**: Pre-commit hooks, GitHub Actions
- **Git Workflow**: Branch strategy, Conventional Commits
- **Code Review**: PR checklist and review process
- **Security**: Sensitive information handling, dependency security
- **Performance**: Performance targets and testing
- **Documentation**: Required documentation and API docs

→ **See `PROJECT_CONSTITUTION.md` for complete guidelines**

---

## Development Workflow

### Typical Development Cycle

1. **Write Test First** (TDD - Red Phase)
   ```powershell
   pytest tests/unit/core/test_your_feature.py -v
   ```
   Confirm the test fails.

2. **Implement Feature** (TDD - Green Phase)
   Write minimal code to make the test pass.
   ```powershell
   pytest tests/unit/core/test_your_feature.py -v
   ```
   Confirm the test passes.

3. **Refactor** (TDD - Refactor Phase)
   Improve code quality while tests pass.
   ```powershell
   make format  # Format code
   make lint    # Check code quality
   pyright jcia tests  # Type check
   ```

4. **Run Full Quality Check**
   ```powershell
   make check   # Run all quality gates
   ```

5. **Commit**
   All pre-commit hooks will run automatically:
   - Ruff lint with auto-fix
   - Ruff format check
   - Pyright type checking
   - Bandit security scan
   - Pytest unit tests
   - Discipline enforcement

### Troubleshooting

**Pre-commit hooks failing?**
```powershell
# Run discipline check manually
powershell -ExecutionPolicy Bypass -File scripts/enforce_discipline.ps1

# Fix format issues
make format

# Fix lint issues
make lint

# Run tests with detailed output
pytest tests/unit -v --tb=short
```

**Type checking errors?**
```powershell
# Run pyright with verbose output
pyright jcia tests -v
```

**Security scan warnings?**
```powershell
# Run bandit with detailed output
bandit -r jcia -c pyproject.toml -f txt -v
```

---

## Quick Reference

### Essential Commands

```powershell
# Environment setup
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
make setup-hooks

# Development workflow
make format          # Format code
make lint           # Check code quality
make check          # Full quality check
make test           # Run all tests

# Specific testing
pytest tests/unit -v --cov=jcia
pyright jcia tests
bandit -r jcia -c pyproject.toml

# Cleanup
make clean
```

### Key Principles

1. **Clean Architecture**: Dependencies point inward
2. **TDD First**: Write tests before production code
3. **Type Safety**: Use Python 3.10+ type hints
4. **Quality Gates**: All checks must pass before commit
5. **Documentation**: Google-style docstrings for all public APIs

---

**For detailed architecture, TDD process, CI/CD workflow, and Git conventions → See PROJECT_CONSTITUTION.md**