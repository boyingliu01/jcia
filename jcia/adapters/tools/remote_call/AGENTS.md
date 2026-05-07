# JCIA Remote Call Adapters - AGENTS.md

**Domain**: Detect remote method calls in Java microservices for cross-service impact analysis.
**Current Level**: 2022 (regex-based). **Target Level**: 2026 (AST/Tree-sitter + service discovery).

## Structure
```
remote_call/
├── __init__.py              # Exports all adapter classes
├── composite_adapter.py     # Orchestrates all adapter subtypes (180 lines)
├── dubbo_adapter.py         # Dubbo RPC detection (120 lines)
├── feign_adapter.py         # Spring Cloud OpenFeign detection (117 lines)
├── http_adapter.py          # HTTP client detection (118 lines)
└── mq_adapter.py            # Message queue detection (146 lines)
```

## HOW EACH ADAPTER WORKS

All adapters follow the same pattern:
1. Import `RemoteCallPatternMatcher` from parent `remote_call_patterns.py`
2. `detect_remote_calls(source_path)` → reads Java file, matches regex patterns, returns `list[RemoteCallInfo]`
3. Each call gets a `confidence` score based on detection method

**Dubbo** — Detects `@DubboReference`, `@DubboService`, `@Reference` (Alibaba) annotations via regex.
**Feign** — Detects `@FeignClient` annotations and interface definitions.
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
| `analyze_cross_service_chain(method, max_hops)` | ❌ Not implemented | Returns `[]` — needs service topology |
| `supported_call_types` | ✅ Implemented | Each adapter returns its types |
| `supports_cross_service` | ✅ Implemented | Returns `False` for all |

## WHAT'S MISSING FOR 2026-LEVEL
1. **AST-based parsing** — Replace regex with Tree-sitter or JavaParser for accurate method resolution
2. **Service registry integration** — Connect to Consul/Nacos/Eureka to resolve service names to actual endpoints
3. **Dynamic call graph** — Build cross-service dependency graph at runtime, not static patterns
4. **gRPC adapter** — `RemoteCallType.GRPC` exists in enum but no adapter implementation
5. **Cross-service chain tracing** — `analyze_cross_service_chain` must trace through service boundaries
6. **Kubernetes awareness** — Service topology from K8s deployments, ingress, service mesh (Istio)
7. **API gateway awareness** — Detect routes through Kong/Apisix/Zuul
8. **Async event propagation** — MQ impact analysis needs topic/queue graph traversal
9. **Configuration-based endpoints** — Parse `application.yml`/`application.properties` for endpoint URLs

## CONVENTIONS
- Adapters are stateless — no shared mutable state between calls
- Pattern matching is case-sensitive for Java annotations
- Confidence scores: 0.95 (string literal), 0.85 (annotation), 0.60 (variable ref)

## ANTI-PATTERNS
- Do NOT add more regex patterns without considering AST alternative — this is the known limitation
- Do NOT implement `analyze_cross_service_chain` with fake data — it needs real topology
- gRPC adapter (`RemoteCallType.GRPC`) exists in enum — DO NOT use it until adapter is implemented
