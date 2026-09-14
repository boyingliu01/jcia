# JCIA Remote Call Adapters - AGENTS.md

**Domain**: Detect remote method calls in Java microservices for cross-service impact analysis.
**Current Level**: regex-based pattern matching (stable). **Target Level**: AST/Tree-sitter + service discovery.

## Structure
```
remote_call/
├── __init__.py              # Exports all adapter classes
├── composite_adapter.py     # Orchestrates all sub-adapters (Dubbo+Feign+gRPC+HTTP+MQ)
├── dubbo_adapter.py         # Dubbo RPC detection (120 lines)
├── feign_adapter.py         # Spring Cloud OpenFeign detection
├── grpc_adapter.py          # gRPC stub detection (XxxGrpc.newBlockingStub etc.)
├── http_adapter.py          # HTTP client detection (RestTemplate/WebClient/OkHttp)
└── mq_adapter.py            # Message queue detection (RabbitMQ/Kafka/RocketMQ)
```

## HOW EACH ADAPTER WORKS

All adapters follow the same pattern:
1. Import `RemoteCallPatternMatcher` from parent `remote_call_patterns.py`
2. `detect_remote_calls(source_path)` → reads Java file, matches regex patterns, returns `list[RemoteCallInfo]`
3. Each call gets a `confidence` score based on detection method

**Dubbo** — Detects `@DubboReference`, `@DubboService`, `@Reference` (Alibaba) annotations via regex.
**Feign** — Detects `@FeignClient` annotations and interface definitions.
**gRPC** — Detects `XxxGrpc.XxxStub` declarations and `XxxGrpc.new(Blocking)Stub` factory calls;
accepts an optional `ServiceRegistry` injection for future cross-service tracing.
**HTTP** — Detects `RestTemplate`, `WebClient`, `OkHttpClient` usage patterns.
**MQ** — Detects `@RabbitListener`, `@KafkaListener`, `@RocketMQMessageListener`.

## Entities Referenced
- `RemoteCallType`: DUBBO, FEIGN, GRPC, REST, MQ_RABBITMQ, MQ_KAFKA, MQ_ROCKETMQ
- `RemoteEndpoint`: service_name, interface, method, url, version, group
- `RemoteCallInfo`: endpoint + call_type + confidence + source_location + metadata
- `RemoteCallChain`: cross-service call chain representation

## Interface Contract (`RemoteCallAnalyzer` ABC)
| Method | Status | Notes |
|--------|--------|-------|
| `detect_remote_calls(path)` | ✅ Implemented | Regex-based pattern matching |
| `analyze_cross_service_chain(method, max_hops)` | ❌ Not implemented | Returns `[]` — needs real topology |
| `supported_call_types` | ✅ Implemented | Each adapter returns its types |
| `supports_cross_service` | ✅ Implemented | Returns `True` for Dubbo/Feign/gRPC/HTTP/MQ |

## WHAT'S MISSING (target level)
1. **AST-based parsing** — Replace regex with Tree-sitter or JavaParser for accurate method resolution
2. **Real service registry** — `ServiceRegistry` ABC + `MockServiceRegistry` exist;
   Consul/Nacos/Eureka adapters still missing
3. **Cross-service chain tracing** — `analyze_cross_service_chain` must trace through
   service boundaries using a populated registry (currently returns `[]`)
4. **Kubernetes awareness** — Service topology from K8s deployments, ingress, service mesh (Istio)
5. **API gateway awareness** — Detect routes through Kong/Apisix/Zuul
6. **Async event propagation** — MQ impact analysis needs topic/queue graph traversal
7. **Configuration-based endpoints** — Parse `application.yml`/`application.properties` for endpoint URLs

## CONVENTIONS
- Adapters are stateless — no shared mutable state between calls
- Pattern matching is case-sensitive for Java annotations
- Confidence scores: 0.95 (string literal), 0.85 (annotation), 0.60 (variable ref)
- Sub-adapters are registered in `CompositeRemoteCallAdapter.__init__` (function-level
  imports are intentional lazy loading)

## ANTI-PATTERNS
- Do NOT add more regex patterns without considering AST alternative — this is the known limitation
- Do NOT implement `analyze_cross_service_chain` with fake data — it needs real topology

## Tests
- `tests/unit/adapters/test_tools/test_remote_call/` — test_adapters.py,
  test_adapters_extended.py, test_grpc_and_registry.py
