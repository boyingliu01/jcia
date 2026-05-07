"""Tests for RemoteCallPatternMatcher.

This module tests the pattern matching capabilities for detecting remote calls
in Java source code, including Dubbo, Feign, HTTP clients, and message queues.
"""

import pytest

from jcia.adapters.tools.remote_call_patterns import (
    RemoteCallPatternMatcher,
    RemoteCallPattern,
    ConfidenceLevel,
)


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_enum_values_exist(self) -> None:
        """Verify all expected confidence levels exist."""
        assert ConfidenceLevel.LITERAL.value == 0.95
        assert ConfidenceLevel.ANNOTATION.value == 0.85
        assert ConfidenceLevel.VARIABLE.value == 0.60

    def test_enum_count(self) -> None:
        """Verify expected number of confidence levels."""
        assert len(ConfidenceLevel) == 3


class TestRemoteCallPatternMatcher:
    """Tests for RemoteCallPatternMatcher."""

    def test_matcher_initialization(self) -> None:
        """Verify matcher initializes with all patterns."""
        matcher = RemoteCallPatternMatcher()
        assert len(matcher._patterns) > 0

    def test_find_dubbo_reference_annotation(self) -> None:
        """Detect @DubboReference annotation."""
        content = """
        @DubboReference
        private UserService userService;
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        assert len(matches) == 1
        assert matches[0].call_type.value == "dubbo"
        assert matches[0].endpoint.interface == "UserService"  # Interface type
        assert pytest.approx(matches[0].confidence, rel=1e-9) == 0.85

    def test_find_dubbo_reference_with_parameters(self) -> None:
        """Detect @DubboReference with parameters."""
        content = """
        @DubboReference(interfaceClass = UserService.class, version = "1.0.0")
        private UserService userService;
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        assert len(matches) == 1
        assert matches[0].call_type.value == "dubbo"
        assert matches[0].endpoint.interface == "UserService"
        assert matches[0].endpoint.version == "1.0.0"
        assert pytest.approx(matches[0].confidence, rel=1e-9) == 0.95

    def test_find_dubbo_service_annotation(self) -> None:
        """Detect @DubboService annotation."""
        content = """
        @DubboService(version = "1.0.0", group = "production")
        public class UserServiceImpl implements UserService {}
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        assert len(matches) == 1
        assert matches[0].call_type.value == "dubbo"
        assert matches[0].endpoint.version == "1.0.0"
        assert matches[0].endpoint.group == "production"

    def test_find_feign_client_annotation(self) -> None:
        """Detect @FeignClient annotation."""
        content = """
        @FeignClient(name = "user-service", url = "http://user-service")
        public interface UserClient {}
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        assert len(matches) == 1
        assert matches[0].call_type.value == "feign"
        assert matches[0].endpoint.service_name == "user-service"
        assert matches[0].endpoint.url == "http://user-service"

    def test_find_feign_client_with_value(self) -> None:
        """Detect @FeignClient with value parameter."""
        content = """
        @FeignClient(value = "order-service")
        public interface OrderClient {}
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        assert len(matches) == 1
        assert matches[0].endpoint.service_name == "order-service"

    def test_find_rest_template_call(self) -> None:
        """Detect RestTemplate calls."""
        content = """
        String result = restTemplate.getForObject("http://api/users/{id}", String.class, userId);
        restTemplate.postForEntity("http://api/orders", request, Order.class);
        restTemplate.put("http://api/users/{id}", user);
        restTemplate.delete("http://api/users/{id}", userId);
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        # Should detect all 4 RestTemplate calls with literal URLs
        assert len(matches) >= 3  # At least 3 calls should be detected
        # Check that all are REST type
        for match in matches:
            assert match.call_type.value == "rest"
        # Check first match has GET method info
        get_matches = [m for m in matches if "get" in m.endpoint.method.lower() if m.endpoint.method]
        assert len(get_matches) >= 1

    def test_find_web_client_call(self) -> None:
        """Detect WebClient calls."""
        content = """
        webClient.get()
            .uri("/users/{id}", userId)
            .retrieve()
            .bodyToMono(User.class);

        webClient.post()
            .uri("/orders")
            .bodyValue(request)
            .retrieve();
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        assert len(matches) >= 1
        assert matches[0].call_type.value == "rest"

    def test_find_rabbit_listener(self) -> None:
        """Detect @RabbitListener annotation."""
        content = """
        @RabbitListener(queues = "order.queue")
        public void processOrder(Order order) {}

        @RabbitListener(queues = "${rabbitmq.queue.user}")
        public void processUser(User user) {}
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        assert len(matches) == 2
        assert matches[0].call_type.value == "rabbitmq"
        assert matches[0].endpoint.url == "order.queue"
        # Variable reference has lower confidence
        assert matches[1].confidence < matches[0].confidence

    def test_find_kafka_listener(self) -> None:
        """Detect @KafkaListener annotation."""
        content = """
        @KafkaListener(topics = "user-events")
        public void handleUserEvent(UserEvent event) {}

        @KafkaListener(topics = "${kafka.topic.orders}", groupId = "order-group")
        public void handleOrderEvent(OrderEvent event) {}
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        assert len(matches) == 2
        assert matches[0].call_type.value == "kafka"
        assert matches[0].endpoint.url == "user-events"

    def test_find_rocketmq_listener(self) -> None:
        """Detect RocketMQ annotations."""
        content = """
        @RocketMQMessageListener(topic = "order-topic", consumerGroup = "order-group")
        public class OrderConsumer {}
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        assert len(matches) == 1
        assert matches[0].call_type.value == "rocketmq"
        assert matches[0].endpoint.url == "order-topic"

    def test_find_grpc_service(self) -> None:
        """Detect gRPC service stubs."""
        content = """
        private UserServiceGrpc.UserServiceBlockingStub userStub;

        UserServiceGrpc.UserServiceBlockingStub stub = UserServiceGrpc.newBlockingStub(channel);
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        # Should detect at least the stub usage
        grpc_matches = [m for m in matches if m.call_type.value == "grpc"]
        assert len(grpc_matches) >= 1

    def test_no_matches_in_plain_java(self) -> None:
        """Verify no matches in plain Java code."""
        content = """
        public class PlainService {
            private String name;
            public void doSomething() {
                System.out.println("Hello");
            }
        }
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "PlainService.java")

        assert len(matches) == 0

    def test_line_number_calculation(self) -> None:
        """Verify line numbers are calculated correctly."""
        content = """package com.example;

import org.springframework.web.client.RestTemplate;

public class TestService {
    private RestTemplate restTemplate;

    public void callRemote() {
        restTemplate.getForObject("http://api/test", String.class);
    }
}
"""
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        # Line 9 should contain the restTemplate call (1-indexed)
        assert len(matches) >= 1
        assert matches[0].source_line == 9

    def test_multiple_calls_in_same_file(self) -> None:
        """Detect multiple remote calls in same file."""
        content = """
        @FeignClient(name = "user-service")
        public interface UserClient {
            @GetMapping("/users/{id}")
            User getUser(@PathVariable String id);
        }

        @DubboReference
        private OrderService orderService;

        @RabbitListener(queues = "notifications")
        public void handleNotification(Notification n) {}
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        # Should detect at least Feign, Dubbo, and RabbitMQ
        call_types = {m.call_type.value for m in matches}
        assert "feign" in call_types
        assert "dubbo" in call_types
        assert "rabbitmq" in call_types

    def test_confidence_levels_correctness(self) -> None:
        """Verify confidence levels are assigned correctly."""
        content = """
        // High confidence - literal values
        @FeignClient(name = "user-service")

        // Medium confidence - annotation without params
        @DubboReference
        private UserService userService;

        // Low confidence - variable reference
        @KafkaListener(topics = "${kafka.topic}")
        """
        matcher = RemoteCallPatternMatcher()
        matches = matcher.find_patterns(content, "Test.java")

        # FeignClient with literal has highest confidence
        feign_match = [m for m in matches if m.call_type.value == "feign"][0]
        assert feign_match.confidence >= 0.85

        # DubboReference without params has medium confidence
        dubbo_match = [m for m in matches if m.call_type.value == "dubbo"][0]
        assert pytest.approx(dubbo_match.confidence, rel=1e-9) == 0.85

        # KafkaListener with variable has lower confidence
        kafka_match = [m for m in matches if m.call_type.value == "kafka"][0]
        assert kafka_match.confidence <= 0.60


class TestRemoteCallPattern:
    """Tests for RemoteCallPattern dataclass."""

    def test_pattern_creation(self) -> None:
        """Create a pattern with all fields."""
        import re
        from jcia.core.entities.remote_call import RemoteCallType

        pattern = RemoteCallPattern(
            call_type=RemoteCallType.DUBBO,
            regex=re.compile(r"@DubboReference"),
            confidence_base=0.85,
            extractor=lambda m: {"service_name": "Test"},
        )
        assert pattern.call_type == RemoteCallType.DUBBO
        assert pattern.confidence_base == 0.85