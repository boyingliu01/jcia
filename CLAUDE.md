# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JCIA (Java Code Impact Analyzer) is a tool for analyzing the impact of code changes in Java projects. It identifies affected classes and methods, intelligently selects test cases, and executes regression testing using clean architecture principles (DDD-style with hexagonal layers).

**Requirements**: Python 3.10+

## Development Methodology

This project follows **SDD (Specification-Driven Development)** and **TDD (Test-Driven Development)**:
- Write specifications before implementation
- Write tests before code
- All new features must have test coverage
- Boy Scout Rule: Every commit improves code quality

## Common Commands

### Development
```bash
make venv              # Create virtual environment
make install           # Install dependencies
make install-dev       # Install development dependencies
make setup-hooks       # Set up pre-commit hooks

# For OpenAI integration
pip install -e ".[ai]"
```

### Testing
```bash
make test              # Run all tests with coverage
make test-unit         # Run only unit tests
make test-integration  # Run only integration tests

# Run a single test
python -m pytest tests/unit/core/test_change_set.py::TestChangeSet::test_is_empty -v

# Run with coverage for specific module
python -m pytest tests/unit --cov=jcia.core.services.analysis_fusion_service --cov-report=term-missing
```

### Code Quality
```bash
make lint              # Run ruff linter
make format            # Format code with ruff
make check             # Run lint + type check + security scan
make security          # Run bandit security scanner

# Type checking (not in make check by default)
python -m pyright jcia
```

### CLI Usage
```bash
jcia analyze --repo-path /path/to/repo --from-commit abc123 --to-commit def456
jcia test --repo-path /path/to/project --target-class com.example.MyClass
jcia regression --repo-path /path/to/project --baseline-commit abc123 --regression-commit def456
jcia report --format html --output ./report.html
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
  - `TestSelectionService`: Selects tests based on impact analysis
  - `ChangeComparisonService`: Compares test runs (baseline vs regression)
  - `SeverityCalculator`, `SeverityEnhancer`: Calculate/enhance impact severity
  - `AnalysisFusionService`: Combines multiple analysis results

- **Use Cases** (`jcia/core/use_cases/`): Application-level orchestration
  - `AnalyzeImpactUseCase`: End-to-end change impact analysis
  - `GenerateTestsUseCase`: Test generation workflow
  - `RunRegressionUseCase`: Execute and compare tests
  - `GenerateReportUseCase`: Create impact reports

- **Adapters** (`jcia/adapters/`): External system integrations
  - `git/pydriller_adapter.py`: Git repository analysis via PyDriller
  - `ai/volcengine_adapter.py`, `ai/openai_adapter.py`, `ai/llm_adapter.py`: AI-powered test generation
  - `ai/skywalking_adapter.py`: SkyWalking trace analysis
  - `database/sqlite_adapter.py`: SQLite persistence
  - `maven/maven_adapter.py`: Maven integration
  - `test_runners/maven_surefire_test_executor.py`: JUnit test execution via Maven Surefire
  - `tools/`:
    - `starts_test_selector_adapter.py`: STARTS algorithm implementation
    - `source_code_call_graph_adapter.py`: Source code-based call graph analysis with reflection detection
    - `java_all_call_graph_adapter.py`: Java method call graph analysis
    - `skywalking_call_chain_adapter.py`: Runtime call chain from SkyWalking
    - `reflection_patterns.py`, `reflection_models.py`: Java reflection call detection and inference
    - `codeql_adapter.py`, `codeql_models.py`: CodeQL semantic analysis integration

- **Reports** (`jcia/reports/`): Output formatting
  - `json_reporter.py`, `html_reporter.py`, `markdown_reporter.py`

### Key Design Patterns

1. **Use Case Pattern**: Each CLI command maps to a use case class that orchestrates the workflow
2. **Repository Pattern**: `SQLiteRepository` abstracts database operations
3. **Adapter Pattern**: External tools (PyDriller, Maven, AI services) wrapped behind interfaces
4. **Request/Response Pattern**: Use cases use dataclass request/response objects
5. **Factory Pattern**: `LLMAdapterFactory` creates appropriate AI adapter based on configuration

### Important Implementation Details

- **Test file detection**: Uses normalized path comparison (`\\` → `/`) for Windows compatibility
- **Severity determination**: `CallChainBuilder._determine_severity()` uses class name keywords (core, manager, handler → HIGH; util, config → LOW)
- **Impact tracing**: Uses BFS/DFS to trace call chains up to `max_depth` levels
- **Test selection**: Supports multiple strategies (ALL, STARTS, IMPACT_BASED, HYBRID)
- **Reflection analysis**: Detects `Class.forName()`, `getMethod()`, `invoke()`, and other reflection patterns with confidence scores

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
- For filesystem-dependent tests: use real temp directories (`tmp_path` fixture) instead of mocking `pathlib.Path.exists` - mocking global path operations doesn't pass context about which path is being checked
- Async tests: `pytest-asyncio` is configured with `loop_scope = function` (see `pytest.ini`)

## Code Conventions

### Test Naming
- Test class format: `Test{ClassName}` (e.g., `TestChangeSet`)
- Test method format: `test_{method_name}_{scenario}` (e.g., `test_add_file_change_success`)

### Type Annotations
- Use Python 3.10+ syntax: `str | None` instead of `Optional[str]`
- All public functions must include type annotations
- Use `TYPE_CHECKING` to avoid circular imports

### Docstrings
- Use Google-style docstrings with Args, Returns, Raises, and Example sections

### Coverage Requirements
- Overall: ≥ 80%
- Entities layer: ≥ 95%
- Services layer: ≥ 85%
- Adapters layer: ≥ 75%

### Ruff Configuration
Per-file ignores are configured for tests:
- `E501`: Line too long (test data/paths)
- `E402`: Module import not at top (sys.path manipulation)
- `S108`: Hardcoded temp file (intentional in tests)

### Import Order
1. Standard library
2. Third-party libraries
3. Local imports (jcia.*)

### Clean Architecture Dependency Rule
Dependencies must point inward: `Adapters → Infrastructure → Use Cases → Services → Entities`
- Entities: No dependencies on external modules
- Services: Only depend on Entities
- Use Cases: Depend on interfaces, not adapters directly
- Adapters: Bridge external systems to core

## SDD Workflow

This project uses Specification-Driven Development. Key files in `.speckit/`:

| File | Purpose |
|------|---------|
| `constitution.md` | Project principles and quality standards |
| `specify.md` | Feature specifications (write before implementation) |
| `plan.md` | Implementation plans |
| `tasks.md` | Task tracking |
| `analyze.md` | Quality metrics and consistency analysis |

When implementing new features:
1. Write/update specification in `specify.md`
2. Create implementation plan in `plan.md`
3. Write tests first (TDD)
4. Implement to pass tests
5. Update `analyze.md` with quality metrics