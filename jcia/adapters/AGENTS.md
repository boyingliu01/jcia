# JCIA Adapters Layer - AGENTS.md

**Domain**: External system integrations (Git, Maven, AI, Database, tools).
**Dependency rule**: Adapters may depend on all internal layers (core, infrastructure).

## Structure
```
adapters/
├── ai/                 # Volcengine, OpenAI, SkyWalking APM, LLM factory
├── database/           # sqlite_database_adapter.py — facade WRAPPING infrastructure layer
├── git/                # PyDriller repository analysis
├── maven/              # Maven build system integration
├── test_runners/       # Maven Surefire + JaCoCo execution
└── tools/              # STARTS, call graphs, CodeQL, reflection, remote call
    └── remote_call/    # Dubbo/Feign/HTTP/MQ detectors + composite (Phase 4, integrated)
```

## WHERE TO LOOK

| Need | File |
|------|------|
| Git commit parsing | `git/pydriller_adapter.py` |
| AI provider factory | `ai/llm_adapter.py` |
| Volcengine LLM | `ai/volcengine_adapter.py` |
| OpenAI LLM | `ai/openai_adapter.py` |
| STARTS test selection | `tools/starts_test_selector_adapter.py` |
| Source code call graph | `tools/source_code_call_graph_adapter.py` |
| Reflection detection | `tools/reflection_patterns.py` |
| SkyWalking traces | `ai/skywalking_adapter.py` |
| Maven Surefire exec | `test_runners/maven_surefire_test_executor.py` |
| Remote call detection | `tools/remote_call/composite_adapter.py` (Dubbo/Feign/HTTP/MQ) |

## CONVENTIONS (adapter-specific)
- Implement interfaces from `jcia/core/interfaces/`
- Transform external data → domain entities
- All adapters must implement the corresponding ABC
- Remote call adapters (`remote_call/`) implement `RemoteCallAnalyzer`; `composite_adapter.py` aggregates the Dubbo/Feign/HTTP/MQ detectors behind one interface

## ANTI-PATTERNS (adapter-specific)
- **NOTE (resolved)** `database/sqlite_database_adapter.py` (`SQLiteDatabaseAdapter`) is the Adapters-layer facade that wraps `jcia/infrastructure/database/sqlite_adapter.py` (`SQLiteAdapter`, low-level SQL). The two files were once both named `sqlite_adapter.py`; the facade was renamed to match its class, so the same-name collision is gone.
- NEVER expose external library types directly — wrap in domain entities
- NEVER catch bare exceptions — specific exception handling only
- NEVER skip interface implementation — pre-commit hooks check this

## Environment variables
- `VOLCENGINE_ACCESS_KEY`, `VOLCENGINE_SECRET_KEY`, `VOLCENGINE_APP_ID`
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`
- `SKYWALKING_OAP_SERVER`, `SKYWALKING_API_TOKEN`
