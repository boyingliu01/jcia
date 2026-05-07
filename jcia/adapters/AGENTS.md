# JCIA Adapters Layer - AGENTS.md

**Domain**: External system integrations (Git, Maven, AI, Database, tools).
**Dependency rule**: Adapters may depend on all internal layers (core, infrastructure).

## Structure
```
adapters/
├── ai/                 # Volcengine, OpenAI, SkyWalking APM, LLM factory
├── database/           # SQLite adapter (WRAPS infrastructure layer)
├── git/                # PyDriller repository analysis
├── maven/              # Maven build system integration
├── test_runners/       # Maven Surefire + JaCoCo execution
└── tools/              # STARTS, call graphs, CodeQL, reflection, remote call
    └── remote_call/    # IN PROGRESS: Dubbo, Feign, HttpClient, MQ
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

## CONVENTIONS (adapter-specific)
- Implement interfaces from `jcia/core/interfaces/`
- Transform external data → domain entities
- All adapters must implement the corresponding ABC
- Remote call adapters (`remote_call/`) are IN PROGRESS

## ANTI-PATTERNS (adapter-specific)
- **KNOWN** `database/sqlite_adapter.py` is confusing — it wraps `jcia/infrastructure/database/sqlite_adapter.py`. Same name, different layer.
- NEVER expose external library types directly — wrap in domain entities
- NEVER catch bare exceptions — specific exception handling only
- NEVER skip interface implementation — pre-commit hooks check this

## Environment variables
- `VOLCENGINE_ACCESS_KEY`, `VOLCENGINE_SECRET_KEY`, `VOLCENGINE_APP_ID`
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`
- `SKYWALKING_OAP_SERVER`, `SKYWALKING_API_TOKEN`
