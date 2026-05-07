# JCIA Core Layer - AGENTS.md

**Domain**: Business logic, entities, services, interfaces, use cases.
**Dependency rule**: Core depends on NOTHING external. Only stdlib.

## Structure
```
core/
├── entities/         # Dataclass domain models (6 files)
├── interfaces/       # ABC contracts (9 files) - excluded from coverage
├── services/         # Domain logic (10 files) - 85%+ coverage target → see services/AGENTS.md
└── use_cases/        # App orchestration (5 files) - request/response pattern
```

## WHERE TO LOOK

| Need | File |
|------|------|
| Entity `__test__ = False` | `entities/test_run.py` - all test entities need this |
| Severity keywords | `services/impact_analysis_service.py` - class name → HIGH/MEDIUM/LOW |
| CALL CHAIN BFS/DFS | `services/call_chain_builder.py` - max_depth limit |
| AI test generation | `services/test_generator_service.py` - factory pattern |
| CLI→UseCase mapping | `use_cases/{analy*impac*,generate_test*,generate_report*,run_regression*}` |

## CONVENTIONS (core-specific)
- **Entities**: `@dataclass`, no external imports, `__test__ = False` on Test*-prefixed classes
- **Interfaces**: ABC + @abstractmethod, excluded from coverage, no implementations
- **Services**: Coordinate entities ONLY, no adapter/infrastructure imports
- **Use cases**: Request/Response dataclass pairs, orchestrate via interfaces
- **Type hints**: Python 3.10+ (`str | None`), `TYPE_CHECKING` for circular refs
- **Docstrings**: Google style (Args/Returns/Raises/Example)

## ANTI-PATTERNS (core-specific)
- NEVER import from `jcia.adapters.*` or `jcia.infrastructure.*` in core
- NEVER skip `__test__ = False` on Test*-prefixed entities (pytest collects them)
- NEVER put business logic in use_cases — belongs in services
- NEVER implement interfaces in core — implementations go in adapters/infrastructure

## Key data flows
1. Impact: UseCase → ChangeSet (entity) → CallChainBuilder → ImpactGraph
2. Test: UseCase → TestCase (entity) → TestSelectionService → selected tests
3. Regression: UseCase → TestRun (entity) → ChangeComparisonService → TestDiff
