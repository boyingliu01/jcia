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
    └── remote_call/    # Microservice remote call adapters
        ├── composite_adapter.py  # Unifies all adapters
        ├── dubbo_adapter.py      # Dubbo RPC detection (regex-based)
        ├── feign_adapter.py      # Feign Client detection (regex-based)
        ├── http_adapter.py       # RestTemplate/WebClient/OkHttp
        ├── mq_adapter.py         # RabbitMQ/Kafka/RocketMQ
        └── __init__.py
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
| **Remote call composite** | `tools/remote_call/composite_adapter.py` |
| **Remote call patterns** | `tools/remote_call_patterns.py` |
| **Dubbo detection** | `tools/remote_call/dubbo_adapter.py` |
| **Feign detection** | `tools/remote_call/feign_adapter.py` |
| **HTTP detection** | `tools/remote_call/http_adapter.py` |
| **MQ detection** | `tools/remote_call/mq_adapter.py` |

## CONVENTIONS (adapter-specific)
- Implement interfaces from `jcia/core/interfaces/`
- Transform external data → domain entities
- All adapters must implement the corresponding ABC
- Remote call adapters (`remote_call/`) implement `RemoteCallAnalyzer` ABC
  - Each adapter uses `RemoteCallPatternMatcher` for regex-based detection
  - Cross-service chain tracing defined in interface but NOT fully implemented yet
  - Current state: 2022-level regex matching; 2026 target: AST/Tree-sitter parsing

## ANTI-PATTERNS (adapter-specific)
- **KNOWN** `database/sqlite_adapter.py` is confusing — it wraps `jcia/infrastructure/database/sqlite_adapter.py`. Same name, different layer.
- NEVER expose external library types directly — wrap in domain entities
- NEVER catch bare exceptions — specific exception handling only
- NEVER skip interface implementation — pre-commit hooks check this

## Environment variables
- `VOLCENGINE_ACCESS_KEY`, `VOLCENGINE_SECRET_KEY`, `VOLCENGINE_APP_ID`
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`
- `SKYWALKING_OAP_SERVER`, `SKYWALKING_API_TOKEN`
