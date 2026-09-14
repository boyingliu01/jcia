# JCIA Adapters/Tools Layer - AGENTS.md

**Domain**: External tool integrations (test selection, call graphs, code analysis, remote calls).
**Layer**: Outermost — bridges external Java analysis tools into JCIA domain entities.

## Structure
```
tools/
├── starts_test_selector_adapter.py     # STARTS algorithm for test selection
├── java_all_call_graph_adapter.py      # Build call chain graphs
├── source_code_call_graph_adapter.py   # Source-level call graph from Java AST
├── skywalking_call_chain_adapter.py    # APM-based call chain from SkyWalking
├── codeql_adapter.py, codeql_models.py # Semantic code analysis via CodeQL
├── reflection_patterns.py, reflection_models.py  # Java reflection detection
├── mock_call_chain_analyzer.py         # Mock for testing
├── remote_call_patterns.py             # Regex pattern matcher (all remote types)
├── remote_call/                        # Microservice remote call adapters
│   ├── composite_adapter.py            # Unifies Dubbo+Feign+gRPC+HTTP+MQ
│   ├── dubbo_adapter.py                # Dubbo RPC (@DubboReference)
│   ├── feign_adapter.py                # Feign Client (@FeignClient)
│   ├── grpc_adapter.py                 # gRPC stubs (XxxGrpc.newXxxStub)
│   ├── http_adapter.py                 # RestTemplate/WebClient/OkHttp
│   └── mq_adapter.py                   # RabbitMQ/Kafka/RocketMQ
└── service_registry/                   # Service discovery adapters
    └── mock_registry.py                # In-memory registry (dev/test, no Consul/Nacos)
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
| Service registry (mock) | `service_registry/mock_registry.py` |

## Remote Call Architecture

```
RemoteCallAnalyzer (ABC interface, jcia.core.interfaces)
├── detect_remote_calls(source_path) → list[RemoteCallInfo]
├── analyze_cross_service_chain(method, max_hops) → list[RemoteCallChain]  # NOT IMPLEMENTED
├── supported_call_types → list[RemoteCallType]
└── supports_cross_service → bool

CompositeRemoteCallAdapter
├── DubboRemoteCallAdapter        → RemoteCallType.DUBBO
├── FeignRemoteCallAdapter        → RemoteCallType.FEIGN
├── GrpcRemoteCallAdapter         → RemoteCallType.GRPC
├── HttpRemoteCallAdapter         → RemoteCallType.REST
└── MessageQueueRemoteCallAdapter → MQ_RABBITMQ, MQ_KAFKA, MQ_ROCKETMQ
```

**Current Implementation State**:
- All adapters use `RemoteCallPatternMatcher` with **regex patterns** on Java source code
- Pattern matcher defines `ConfidenceLevel`: LITERAL (0.95), ANNOTATION (0.85), VARIABLE (0.60)
- gRPC detection covers `XxxGrpc.XxxStub` and `XxxGrpc.new(Blocking)Stub` patterns
- `ServiceRegistry` interface (core) + `MockServiceRegistry` (adapter) exist; gRPC adapter
  accepts an optional registry injection but cross-service tracing is still `[]`
- No AST/Tree-sitter parsing — cannot handle dynamic dispatch or runtime routing
- **Remaining gaps**: AST-based parsing, real registry (Consul/Nacos), Kubernetes
  service topology, API gateway awareness, async event-driven MQ impact propagation

## Entities Used
- `jcia.core.entities.remote_call`: RemoteCallType, RemoteEndpoint, RemoteCallInfo, RemoteCallChain

## CONVENTIONS
- All adapters import entities from `jcia.core.entities.*`, interfaces from `jcia.core.interfaces.*`
- Remote call adapters import `RemoteCallPatternMatcher` from sibling `remote_call_patterns.py`
- Confidence scores are attached to detected calls (0.0–1.0 range)
- Layering is machine-enforced: see repo-root `architecture.yaml` + `[tool.importlinter]`

## ANTI-PATTERNS
- NEVER use bare `except:` in adapter code — use specific exception types
- NEVER expose external tool formats directly — transform to domain entities first
- Do NOT extend regex patterns without writing tests — pattern changes break detection

## Tests
- `tests/unit/adapters/test_tools/test_remote_call/` — 44 tests (adapters, extended, grpc+registry)
- `tests/unit/adapters/test_tools/` — tools layer unit tests
