# JCIA Core Services Layer - AGENTS.md

**Domain**: Business logic and domain operations. Coordinates entities. No adapter/infrastructure imports.
**Dependency Rule**: Services depend ONLY on entities and interfaces from core layer.
This rule is machine-enforced by import-linter (`[tool.importlinter]` in pyproject.toml,
contracts declared in repo-root `architecture.yaml`; run `make arch-check` or `lint-imports`).

## Structure
```
services/
├── __init__.py
├── impact_analysis_service.py       # Core impact analysis
├── call_chain_builder.py            # BFS/DFS call chain traversal
├── change_comparison_service.py     # Diff between commits
├── test_selection_service.py        # Test case selection logic
├── test_generator_service.py        # AI test generation factory
├── severity_calculator.py           # Impact severity scoring
├── severity_enhancer.py             # Multi-dimension severity enhancement
├── analysis_fusion_service.py       # Fusion: local + remote + severity (largest service)
└── remote_call_detection_service.py # Remote call detection orchestration
```

## WHERE TO LOOK

| Need | File | Key Classes/Methods |
|------|------|---------------------|
| Impact analysis flow | `impact_analysis_service.py` | `ImpactAnalysisService.analyze()` |
| Call chain BFS/DFS | `call_chain_builder.py` | `CallChainBuilder.bfs()`, `dfs()` |
| Commit diff | `change_comparison_service.py` | `ChangeComparisonService.compare()` |
| Test selection | `test_selection_service.py` | `TestSelectionService.select_tests()` |
| AI test generation | `test_generator_service.py` | `TestGeneratorService.generate()` |
| Severity scoring | `severity_calculator.py` | `SeverityCalculator.calculate()` |
| Multi-dimension severity | `severity_enhancer.py` | `SeverityEnhancer.enhance()` |
| **Microservice fusion** | `analysis_fusion_service.py` | `AnalysisFusionService.fuse()` |
| **Remote call detection** | `remote_call_detection_service.py` | `RemoteCallDetectionService.detect_from_file()` |

## KEY DATA FLOWS

1. **Impact Analysis**: `ChangeSet` → `CallChainBuilder` → `ImpactGraph` (affected classes/methods)
2. **Remote Call Detection**: `RemoteCallDetectionService(analyzer=...)` → `RemoteCallInfo` list
3. **Microservice Fusion**: `AnalysisFusionService` merges local call graph + remote calls + severity
4. **Regression**: baseline `TestRun` vs regression `TestRun` → `ChangeComparisonService` → diff

## CONVENTIONS
- NO imports from `jcia.adapters.*` or `jcia.infrastructure.*` — use interfaces (ABC) only
- `RemoteCallDetectionService` takes a **required** `analyzer: RemoteCallAnalyzer` constructor
  argument; the concrete implementation (e.g. `CompositeRemoteCallAdapter`) is wired in by
  the composition root (`jcia/cli/main.py`), never by the service itself
- Use `TYPE_CHECKING` for circular references
- Business logic lives here, NOT in use_cases

## ANTI-PATTERNS
- NEVER import adapter implementations directly — inject via interfaces
  (import-linter will block the commit: `core 层不得依赖外层实现` contract)
- NEVER put orchestration logic here — that belongs in use_cases
- `analysis_fusion_service.py` is ~900 lines — consider splitting before adding complexity

## Tests
- `tests/unit/core/test_services/` — 7 test files
