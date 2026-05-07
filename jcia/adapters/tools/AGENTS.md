# JCIA Adapters/Tools Layer - AGENTS.md

**Domain**: External tool integrations (test selection, call graphs, code analysis, remote calls).
**Layer**: Outermost — bridges external Java analysis tools into JCIA domain entities.

## Structure
```
tools/
├── starts_test_selector_adapter.py     # STARTS algorithm for test selection
├── java_all_call_graph_adapter.py      # Build call chain graphs (914 lines)
├── source_code_call_graph_adapter.py   # Source-level call graph from Java AST
├── skywalking_call_chain_adapter.py    # APM-based call chain from SkyWalking
├── codeql_adapter.py, codeql_models.py # Semantic code analysis via CodeQL
├── reflection_patterns.py, reflection_models.py  # Java reflection detection
├── mock_call_chain_analyzer.py         # Mock for testing
├── remote_call_patterns.py             # Regex pattern matcher (566 lines)
└── remote_call/                        # Microservice remote call adapters
    ├── __init__.py
    ├── composite_adapter.py            # Unifies Dubbo+Feign+HTTP+MQ (180 lines)
    ├── dubbo_adapter.py                # Dubbo RPC (@DubboReference) (120 lines)
    ├── feign_adapter.py                # Feign Client (@FeignClient) (117 lines)
    ├── http_adapter.py                 # RestTemplate/WebClient/OkHttp (118 lines)
    └── mq_adapter.py                   # RabbitMQ/Kafka/RocketMQ (146 lines)
```

## WHERE TO LOOK

| Need | File |
|------|------|
| STARTS test selection | `starts_test_selector_adapter.py` |
| Full call graph | `java_all_call_graph_adapter.py` |
| Source-level call graph | `source_code_call_graph_adapter.py` |
| APM call chains | `skywalking_call_chain_adapter.py` |
| CodeQL queries | `codeql_adapter.py` |
| Reflection patterns | `reflection_patterns.py` |
| Remote call detection | `remote_call/composite_adapter.py` |
| Pattern definitions | `remote_call_patterns.py` |

## Remote Call Architecture

```
RemoteCallAnalyzer (ABC interface)
├── detect_remote_calls(source_path) → list[RemoteCallInfo]
├── analyze_cross_service_chain(method, max_hops) → list[RemoteCallChain]  # NOT IMPLEMENTED
├── supported_call_types → list[RemoteCallType]
└── supports_cross_service → bool

CompositeRemoteCallAdapter
├── DubboRemoteCallAdapter     → RemoteCallType.DUBBO
├── FeignRemoteCallAdapter     → RemoteCallType.FEIGN
├── HttpRemoteCallAdapter      → RemoteCallType.REST
└── MessageQueueRemoteCallAdapter → MQ_RABBITMQ, MQ_KAFKA, MQ_ROCKETMQ
```

**Current Implementation State** (2022-level):
- All adapters use `RemoteCallPatternMatcher` with **regex patterns** on Java source code
- Pattern matcher defines `ConfidenceLevel`: LITERAL (0.95), ANNOTATION (0.85), VARIABLE (0.60)
- No AST/Tree-sitter parsing — cannot handle dynamic dispatch, service discovery, or runtime routing
- `analyze_cross_service_chain` is abstract in interface but returns `[]` in all adapters
- **Missing for 2026**: AST-based parsing, service registry integration (Consul/Nacos), gRPC adapter, Kubernetes service topology, API gateway awareness, async event-driven MQ impact propagation

## Entities Used
- `jcia.core.entities.remote_call`: RemoteCallType, RemoteEndpoint, RemoteCallInfo, RemoteCallChain

## CONVENTIONS
- All adapters import entities from `jcia.core.entities.*`, interfaces from `jcia.core.interfaces.*`
- Remote call adapters import `RemoteCallPatternMatcher` from sibling `remote_call_patterns.py`
- Confidence scores are attached to detected calls (0.0–1.0 range)

## ANTI-PATTERNS
- NEVER use bare `except:` in adapter code — use specific exception types
- NEVER expose external tool formats directly — transform to domain entities first
- Do NOT extend regex patterns without writing tests — pattern changes break detection

## Tests
- `tests/unit/adapters/test_tools/test_remote_call/` — 3 test files
- `tests/unit/adapters/test_tools/` — 8 test files (tools layer total)
