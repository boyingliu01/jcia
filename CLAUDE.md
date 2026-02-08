# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JCIA (Java Code Impact Analyzer) is a tool for analyzing the impact of code changes in Java projects. It identifies affected classes and methods, intelligently selects test cases, and executes regression testing using clean architecture principles (DDD-style with hexagonal layers).

## Common Commands

### Development
```bash
make venv              # Create virtual environment
make install           # Install dependencies
make install-dev        # Install development dependencies
make setup-hooks       # Set up pre-commit hooks
```

### Testing
```bash
make test              # Run all tests with coverage
make test-unit         # Run only unit tests
make test-integration  # Run only integration tests

# Run a single test
python -m pytest tests/unit/core/test_change_set.py::TestChangeSet::test_is_empty -v
```

### Code Quality
```bash
make lint              # Run ruff linter
make format            # Format code with ruff
make check             # Run lint + type check + security scan
make security          # Run bandit security scanner
```

### CLI Usage
```bash
jcia analyze --repo-path /path/to/repo --from-commit abc123 --to-commit def456
jcia test --repo-path /path/to/project --target-class com.example.MyClass
jcia config --show
```

## Architecture

### Layer Structure
- **Entities** (`jcia/core/entities/`): Core domain models with no dependencies on other layers
  - `ChangeSet`: Git change collection (files, methods, commits)
  - `ImpactGraph`: Method call dependency graph with severity levels
  - `TestCase`: Generated test case with priority and coverage info
  - `TestRun`, `TestResult`, `TestDiff`: Test execution and comparison models

- **Interfaces** (`jcia/core/interfaces/`): Abstract contracts for adapters
  - `ChangeAnalyzer`: Analyze Git commits/changes (implemented by `PyDrillerAdapter`)
  - `CallChainAnalyzer`: Analyze method call dependencies
  - `TestSelector`, `TestGenerator`, `TestExecutor`: Test-related abstractions
  - `AIService`: AI service for test generation (Volcengine, LLM)

- **Services** (`jcia/core/services/`): Domain logic coordinating entities
  - `CallChainBuilder`: Builds impact graphs from method changes
  - `ImpactAnalysisService`: Analyzes change propagation through call chains
  - `TestGeneratorService`: Coordinates test generation via AI
  - `ChangeComparisonService`: Compares test runs (baseline vs regression)

- **Use Cases** (`jcia/core/use_cases/`): Application-level orchestration
  - `AnalyzeImpactUseCase`: End-to-end change impact analysis
  - `GenerateTestsUseCase`: Test generation workflow
  - `RunRegressionUseCase`: Execute and compare tests
  - `GenerateReportUseCase`: Create impact reports

- **Adapters** (`jcia/adapters/`): External system integrations
  - `git/pydriller_adapter.py`: Git repository analysis via PyDriller
  - `ai/volcengine_adapter.py`: AI-powered test generation
  - `database/sqlite_adapter.py`: SQLite persistence

- **Reports** (`jcia/reports/`): Output formatting
  - `json_reporter.py`, `html_reporter.py`, `markdown_reporter.py`

### Key Design Patterns

1. **Use Case Pattern**: Each CLI command maps to a use case class that orchestrates the workflow
2. **Repository Pattern**: `SQLiteRepository` abstracts database operations
3. **Adapter Pattern**: External tools (PyDriller, Maven, AI services) wrapped behind interfaces
4. **Request/Response Pattern**: Use cases use dataclass request/response objects

### Important Implementation Details

- **Test file detection**: Uses normalized path comparison (`\\` → `/`) for Windows compatibility
- **Severity determination**: `CallChainBuilder._determine_severity()` uses class name keywords (core, manager, handler → HIGH; util, config → LOW)
- **Impact tracing**: Uses BFS/DFS to trace call chains up to `max_depth` levels
- **Test selection**: Supports multiple strategies (ALL, STARTS, IMPACT_BASED, HYBRID)

### Data Flow: Impact Analysis
1. `AnalyzeImpactUseCase.execute()` receives commit range
2. `PyDrillerAdapter.analyze_commits()` extracts `ChangeSet`
3. `ImpactAnalysisService.analyze()` uses `CallChainAnalyzer` to build dependency graph
4. `ImpactGraph` generated with nodes (methods) and edges (calls) + severity levels
5. Summary statistics returned via `AnalyzeImpactResponse`

### Test Entity Anti-Pattern Prevention
The `TestStatus`, `TestResult`, `TestRun`, `TestDiff`, and related test entities have `__test__ = False` attribute to prevent pytest from collecting them as test classes (see `jcia/core/entities/test_run.py`).

## Configuration

Configuration files searched in order:
- `.jcia.yaml` (preferred)
- `jcia.yaml`

Environment variables for AI features:
- `VOLCENGINE_ACCESS_KEY`
- `VOLCENGINE_SECRET_KEY`
- `VOLCENGINE_APP_ID`

## Testing Notes

- Test fixtures defined in `tests/conftest_base.py`
- Unit tests in `tests/unit/` organized by layer (core, adapters, infrastructure)
- Integration tests in `tests/integration/`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Tests follow AAA pattern (Arrange, Act, Assert) with descriptive names
