# JCIA Core Services Layer - AGENTS.md

**Domain**: Business logic and domain operations. Coordinates entities. No adapter/infrastructure imports.
**Dependency Rule**: Services depend ONLY on entities and interfaces from core layer.

## Structure
```
services/
├── __init__.py
├── impact_analysis_service.py      # Core impact analysis (8.7KB)
├── call_chain_builder.py           # BFS/DFS call chain traversal (7.8KB)
├── change_comparison_service.py    # Diff between commits (9.6KB)
├── test_selection_service.py       # Test case selection logic (10.8KB)
├── test_generator_service.py       # AI test generation factory (7KB)
├── severity_calculator.py          # Impact severity scoring (16.3KB)
├── severity_enhancer.py            # Multi-dimension severity enhancement (5KB)
├── analysis_fusion_service.py      # Fusion: local + remote + severity (30.3KB, 894 lines)
└── remote_call_detection_service.py # Remote call detection orchestration (9.1KB)
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
| **Microservice fusion** | `analysis_fusion_service.py` | `AnalysisFusionService.fuse()` — 894 lines |
| **Remote call detection** | `remote_call_detection_service.py` | `RemoteCallDetectionService.detect()` |

## KEY DATA FLOWS

1. **Impact Analysis**: `ChangeSet` → `CallChainBuilder` → `ImpactGraph` (affected classes/methods)
2. **Remote Call Detection**: `RemoteCallDetectionService` → adapters → `RemoteCallInfo` list
3. **Microservice Fusion**: `AnalysisFusionService` merges local call graph + remote calls + severity
4. **Test Selection**: `ImpactGraph` + `remote_call_detection_service.py` → `RemoteCallInfo` list
4. **Regression**: baseline `TestRun` vs regression `TestRun` → `ChangeComparisonService` → diff

## CONVENTIONS
- NO imports from `jcia.adapters.*` or `jcia.infrastructure.*` — use interfaces (ABC) only
- Use `TYPE_CHECKING` for circular references
- Business logic lives here, NOT in use_cases

## ANTI-PATTERNS
- NEVER import adapter implementations directly — inject via interfaces
- NEVER put orchestration logic here — that belongs in use_cases
- `analysis_fusion_service.py` is 894 lines — consider splitting if adding complexity

## Tests
- `tests/unit/core/test_services/` — 7 test files
- `tests/unit/core/services/` — 2 test files (legacy naming)
