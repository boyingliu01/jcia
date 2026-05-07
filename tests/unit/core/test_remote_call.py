"""Tests for remote call entities.

This module tests the RemoteCallType, RemoteEndpoint, and RemoteCallInfo entities.
"""

import pytest

from jcia.core.entities.remote_call import (
    RemoteCallInfo,
    RemoteCallType,
    RemoteEndpoint,
    RemoteCallChain,
)


class TestRemoteCallType:
    """Tests for RemoteCallType enum."""

    def test_enum_values_exist(self) -> None:
        """Verify all expected call types exist."""
        assert RemoteCallType.DUBBO.value == "dubbo"
        assert RemoteCallType.FEIGN.value == "feign"
        assert RemoteCallType.GRPC.value == "grpc"
        assert RemoteCallType.REST.value == "rest"
        assert RemoteCallType.MQ_RABBITMQ.value == "rabbitmq"
        assert RemoteCallType.MQ_KAFKA.value == "kafka"
        assert RemoteCallType.MQ_ROCKETMQ.value == "rocketmq"

    def test_enum_count(self) -> None:
        """Verify expected number of call types."""
        assert len(RemoteCallType) == 7

    def test_enum_is_rpc_type(self) -> None:
        """Verify RPC type check."""
        assert RemoteCallType.DUBBO.is_rpc() is True
        assert RemoteCallType.FEIGN.is_rpc() is True
        assert RemoteCallType.GRPC.is_rpc() is True
        assert RemoteCallType.REST.is_rpc() is True
        assert RemoteCallType.MQ_RABBITMQ.is_rpc() is False
        assert RemoteCallType.MQ_KAFKA.is_rpc() is False
        assert RemoteCallType.MQ_ROCKETMQ.is_rpc() is False

    def test_enum_is_message_queue(self) -> None:
        """Verify message queue type check."""
        assert RemoteCallType.DUBBO.is_message_queue() is False
        assert RemoteCallType.FEIGN.is_message_queue() is False
        assert RemoteCallType.MQ_RABBITMQ.is_message_queue() is True
        assert RemoteCallType.MQ_KAFKA.is_message_queue() is True
        assert RemoteCallType.MQ_ROCKETMQ.is_message_queue() is True


class TestRemoteEndpoint:
    """Tests for RemoteEndpoint dataclass."""

    def test_create_endpoint_with_all_fields(self) -> None:
        """Create endpoint with all fields."""
        endpoint = RemoteEndpoint(
            service_name="user-service",
            interface="com.example.UserService",
            method="getUserById",
            url="http://user-service/api/users/{id}",
            version="1.0.0",
            group="production",
        )
        assert endpoint.service_name == "user-service"
        assert endpoint.interface == "com.example.UserService"
        assert endpoint.method == "getUserById"
        assert endpoint.url == "http://user-service/api/users/{id}"
        assert endpoint.version == "1.0.0"
        assert endpoint.group == "production"

    def test_create_endpoint_with_minimal_fields(self) -> None:
        """Create endpoint with minimal fields."""
        endpoint = RemoteEndpoint(service_name="order-service")
        assert endpoint.service_name == "order-service"
        assert endpoint.interface is None
        assert endpoint.method is None
        assert endpoint.url is None
        assert endpoint.version is None
        assert endpoint.group is None

    def test_endpoint_default_values(self) -> None:
        """Verify endpoint default values are None."""
        endpoint = RemoteEndpoint()
        assert endpoint.service_name is None
        assert endpoint.interface is None
        assert endpoint.method is None

    def test_endpoint_full_identifier(self) -> None:
        """Verify full_identifier property."""
        endpoint = RemoteEndpoint(
            service_name="user-service",
            interface="com.example.UserService",
            method="getUserById",
        )
        assert endpoint.full_identifier == "user-service:com.example.UserService.getUserById"

    def test_endpoint_full_identifier_without_service(self) -> None:
        """Verify full_identifier without service name."""
        endpoint = RemoteEndpoint(
            interface="com.example.UserService",
            method="getUserById",
        )
        assert endpoint.full_identifier == "com.example.UserService.getUserById"

    def test_endpoint_full_identifier_without_interface(self) -> None:
        """Verify full_identifier without interface."""
        endpoint = RemoteEndpoint(
            service_name="user-service",
            method="getUserById",
        )
        assert endpoint.full_identifier == "user-service.getUserById"

    def test_endpoint_full_identifier_empty(self) -> None:
        """Verify full_identifier when all optional fields are None."""
        endpoint = RemoteEndpoint()
        assert endpoint.full_identifier == ""

    def test_endpoint_is_complete(self) -> None:
        """Verify is_complete property."""
        complete_endpoint = RemoteEndpoint(
            service_name="svc",
            interface="Iface",
            method="method",
        )
        assert complete_endpoint.is_complete() is True

        incomplete_endpoint = RemoteEndpoint(service_name="svc")
        assert incomplete_endpoint.is_complete() is False


class TestRemoteCallInfo:
    """Tests for RemoteCallInfo dataclass."""

    def test_create_call_info_with_all_fields(self) -> None:
        """Create call info with all fields."""
        endpoint = RemoteEndpoint(
            service_name="user-service",
            interface="UserService",
            method="getUser",
        )
        call_info = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="com.example.OrderController",
            caller_method="createOrder",
            confidence=0.95,
            source_line=42,
            source_file="OrderController.java",
            annotation="@DubboReference",
            metadata={"timeout": 5000},
        )
        assert call_info.call_type == RemoteCallType.DUBBO
        assert call_info.endpoint.service_name == "user-service"
        assert call_info.caller_class == "com.example.OrderController"
        assert call_info.caller_method == "createOrder"
        assert call_info.confidence == 0.95
        assert call_info.source_line == 42
        assert call_info.source_file == "OrderController.java"
        assert call_info.annotation == "@DubboReference"
        assert call_info.metadata == {"timeout": 5000}

    def test_create_call_info_with_defaults(self) -> None:
        """Create call info with default values."""
        endpoint = RemoteEndpoint(service_name="svc")
        call_info = RemoteCallInfo(
            call_type=RemoteCallType.FEIGN,
            endpoint=endpoint,
            caller_class="Test",
        )
        assert call_info.confidence == 0.8  # Default confidence
        assert call_info.source_line == 0
        assert call_info.source_file == ""
        assert call_info.annotation is None
        assert call_info.metadata == {}

    def test_is_high_confidence_threshold_0_9(self) -> None:
        """Verify is_high_confidence uses 0.9 threshold."""
        endpoint = RemoteEndpoint(service_name="svc")

        high_confidence = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="Test",
            confidence=0.95,
        )
        assert high_confidence.is_high_confidence() is True

        at_threshold = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="Test",
            confidence=0.9,
        )
        assert at_threshold.is_high_confidence() is True

        below_threshold = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="Test",
            confidence=0.89,
        )
        assert below_threshold.is_high_confidence() is False

    def test_full_call_signature(self) -> None:
        """Verify full_call_signature property."""
        endpoint = RemoteEndpoint(
            service_name="user-service",
            method="getUserById",
        )
        call_info = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="OrderService",
            caller_method="processOrder",
        )
        assert call_info.full_call_signature == "OrderService.processOrder -> user-service.getUserById"

    def test_full_call_signature_without_caller_method(self) -> None:
        """Verify full_call_signature without caller method."""
        endpoint = RemoteEndpoint(method="getUserById")
        call_info = RemoteCallInfo(
            call_type=RemoteCallType.FEIGN,
            endpoint=endpoint,
            caller_class="OrderService",
        )
        assert call_info.full_call_signature == "OrderService -> getUserById"

    def test_call_info_implements_test_false(self) -> None:
        """Verify __test__ = False to prevent pytest collection."""
        endpoint = RemoteEndpoint(service_name="svc")
        call_info = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="Test",
        )
        assert call_info.__test__ is False

    def test_call_info_metadata_operations(self) -> None:
        """Test metadata field operations."""
        endpoint = RemoteEndpoint(service_name="svc")
        call_info = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="Test",
            metadata={"key1": "value1", "timeout": 5000},
        )
        assert call_info.metadata["key1"] == "value1"
        assert call_info.metadata["timeout"] == 5000

        # Test that metadata is a copy (mutable)
        call_info.metadata["new_key"] = "new_value"
        assert call_info.metadata["new_key"] == "new_value"

    def test_call_info_str_representation(self) -> None:
        """Test string representation through full_call_signature."""
        endpoint = RemoteEndpoint(service_name="user-service", method="getUser")
        call_info = RemoteCallInfo(
            call_type=RemoteCallType.FEIGN,
            endpoint=endpoint,
            caller_class="OrderController",
            caller_method="createOrder",
            confidence=0.95,
        )
        signature = call_info.full_call_signature
        assert "OrderController.createOrder" in signature
        assert "user-service" in signature
        assert "getUser" in signature

    def test_call_info_confidence_edge_cases(self) -> None:
        """Test confidence value edge cases."""
        endpoint = RemoteEndpoint(service_name="svc")

        # Test confidence = 0.0
        call_low = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="Test",
            confidence=0.0,
        )
        assert call_low.is_high_confidence() is False

        # Test confidence = 1.0
        call_high = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="Test",
            confidence=1.0,
        )
        assert call_high.is_high_confidence() is True

        # Test confidence exactly at threshold (0.9)
        call_threshold = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="Test",
            confidence=0.9,
        )
        assert call_threshold.is_high_confidence() is True

    def test_call_info_with_empty_endpoint(self) -> None:
        """Test RemoteCallInfo with minimal/empty endpoint."""
        empty_endpoint = RemoteEndpoint()
        call_info = RemoteCallInfo(
            call_type=RemoteCallType.REST,
            endpoint=empty_endpoint,
            caller_class="TestController",
            caller_method="testMethod",
        )
        assert call_info.endpoint.full_identifier == ""
        assert call_info.full_call_signature == "TestController.testMethod -> "


class TestRemoteCallChain:
    """Tests for RemoteCallChain dataclass."""

    def test_create_chain(self) -> None:
        """Create a remote call chain."""
        endpoint1 = RemoteEndpoint(service_name="svc1", method="method1")
        endpoint2 = RemoteEndpoint(service_name="svc2", method="method2")

        call1 = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint1,
            caller_class="A",
            caller_method="a",
        )
        call2 = RemoteCallInfo(
            call_type=RemoteCallType.FEIGN,
            endpoint=endpoint2,
            caller_class="B",
            caller_method="b",
        )

        chain = RemoteCallChain(
            calls=[call1, call2],
            source_method="com.example.Start.method",
            target_service="svc2",
        )
        assert len(chain.calls) == 2
        assert chain.source_method == "com.example.Start.method"
        assert chain.target_service == "svc2"

    def test_chain_hop_count(self) -> None:
        """Verify hop_count property."""
        endpoint1 = RemoteEndpoint(service_name="svc1")
        endpoint2 = RemoteEndpoint(service_name="svc2")
        endpoint3 = RemoteEndpoint(service_name="svc3")

        call1 = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO, endpoint=endpoint1, caller_class="A"
        )
        call2 = RemoteCallInfo(
            call_type=RemoteCallType.FEIGN, endpoint=endpoint2, caller_class="B"
        )
        call3 = RemoteCallInfo(
            call_type=RemoteCallType.REST, endpoint=endpoint3, caller_class="C"
        )

        chain = RemoteCallChain(
            calls=[call1, call2, call3],
            source_method="start",
            target_service="svc3",
        )
        assert chain.hop_count() == 3

    def test_chain_default_values(self) -> None:
        """Verify default values."""
        chain = RemoteCallChain(
            calls=[],
            source_method="start",
        )
        assert chain.calls == []
        assert chain.target_service is None
        assert chain.total_confidence == 0.0

    def test_chain_get_unique_services(self) -> None:
        """Verify unique services extraction."""
        endpoint1 = RemoteEndpoint(service_name="svc1")
        endpoint2 = RemoteEndpoint(service_name="svc2")
        endpoint3 = RemoteEndpoint(service_name="svc1")  # Duplicate

        call1 = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO, endpoint=endpoint1, caller_class="A"
        )
        call2 = RemoteCallInfo(
            call_type=RemoteCallType.FEIGN, endpoint=endpoint2, caller_class="B"
        )
        call3 = RemoteCallInfo(
            call_type=RemoteCallType.REST, endpoint=endpoint3, caller_class="C"
        )

        chain = RemoteCallChain(calls=[call1, call2, call3], source_method="start")
        unique_services = chain.get_unique_services()
        assert unique_services == {"svc1", "svc2"}

    def test_chain_calculate_total_confidence(self) -> None:
        """Verify total confidence calculation."""
        endpoint1 = RemoteEndpoint(service_name="svc1")
        endpoint2 = RemoteEndpoint(service_name="svc2")

        call1 = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint1,
            caller_class="A",
            confidence=0.9,
        )
        call2 = RemoteCallInfo(
            call_type=RemoteCallType.FEIGN,
            endpoint=endpoint2,
            caller_class="B",
            confidence=0.8,
        )

        chain = RemoteCallChain(calls=[call1, call2], source_method="start")
        # Average confidence: (0.9 + 0.8) / 2 = 0.85
        assert pytest.approx(chain.calculate_total_confidence(), rel=1e-9) == 0.85

    def test_chain_with_single_call(self) -> None:
        """Verify chain with single call works correctly."""
        endpoint = RemoteEndpoint(service_name="single-svc", method="method")
        call = RemoteCallInfo(
            call_type=RemoteCallType.GRPC,
            endpoint=endpoint,
            caller_class="Caller",
            caller_method="call",
            confidence=0.95,
        )

        chain = RemoteCallChain(calls=[call], source_method="source")
        assert chain.hop_count() == 1
        assert chain.calculate_total_confidence() == 0.95
        assert chain.get_unique_services() == {"single-svc"}

    def test_chain_with_many_calls(self) -> None:
        """Verify chain with many calls calculates correctly."""
        calls = []
        for i in range(5):
            endpoint = RemoteEndpoint(service_name=f"svc{i}", method=f"method{i}")
            call = RemoteCallInfo(
                call_type=RemoteCallType.REST,
                endpoint=endpoint,
                caller_class=f"Class{i}",
                confidence=0.8 + i * 0.02,  # 0.8, 0.82, 0.84, 0.86, 0.88
            )
            calls.append(call)

        chain = RemoteCallChain(calls=calls, source_method="start")
        assert chain.hop_count() == 5

        # Average: (0.8 + 0.82 + 0.84 + 0.86 + 0.88) / 5 = 4.2 / 5 = 0.84
        expected_avg = sum(c.confidence for c in calls) / len(calls)
        assert pytest.approx(chain.calculate_total_confidence(), rel=1e-9) == expected_avg

    def test_chain_with_duplicate_services(self) -> None:
        """Verify duplicate services are handled correctly."""
        # Create calls that go through the same service multiple times
        endpoint1 = RemoteEndpoint(service_name="shared-svc", method="method1")
        endpoint2 = RemoteEndpoint(service_name="shared-svc", method="method2")
        endpoint3 = RemoteEndpoint(service_name="other-svc", method="method3")

        call1 = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO, endpoint=endpoint1, caller_class="A"
        )
        call2 = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO, endpoint=endpoint2, caller_class="B"
        )
        call3 = RemoteCallInfo(
            call_type=RemoteCallType.FEIGN, endpoint=endpoint3, caller_class="C"
        )

        chain = RemoteCallChain(calls=[call1, call2, call3], source_method="start")

        # Should only have 2 unique services
        unique = chain.get_unique_services()
        assert unique == {"shared-svc", "other-svc"}
        assert len(unique) == 2

    def test_chain_calculate_total_confidence_with_empty_chain(self) -> None:
        """Verify confidence calculation with empty chain returns 0.0."""
        chain = RemoteCallChain(calls=[], source_method="start")
        assert chain.calculate_total_confidence() == 0.0

    def test_chain_with_endpoint_without_service_name(self) -> None:
        """Verify chain handles endpoints without service names."""
        # Some endpoints might not have service names set
        endpoint1 = RemoteEndpoint(method="method1")  # No service_name
        endpoint2 = RemoteEndpoint(service_name="svc2", method="method2")

        call1 = RemoteCallInfo(
            call_type=RemoteCallType.REST, endpoint=endpoint1, caller_class="A"
        )
        call2 = RemoteCallInfo(
            call_type=RemoteCallType.REST, endpoint=endpoint2, caller_class="B"
        )

        chain = RemoteCallChain(calls=[call1, call2], source_method="start")

        # Should only get svc2, not the empty one
        unique = chain.get_unique_services()
        assert unique == {"svc2"}

    def test_chain_implements_test_false(self) -> None:
        """Verify __test__ = False to prevent pytest collection."""
        chain = RemoteCallChain(calls=[], source_method="start")
        assert chain.__test__ is False