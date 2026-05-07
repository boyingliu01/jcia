"""Tests for remote call adapters.

This module tests all remote call adapters including Dubbo, Feign, HTTP, and MQ.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from jcia.adapters.tools.remote_call import (
    CompositeRemoteCallAdapter,
    DubboRemoteCallAdapter,
    FeignRemoteCallAdapter,
    HttpRemoteCallAdapter,
    MessageQueueRemoteCallAdapter,
)
from jcia.core.entities.remote_call import RemoteCallType


class TestDubboRemoteCallAdapter:
    """Tests for DubboRemoteCallAdapter."""

    def test_adapter_initialization(self) -> None:
        """Verify adapter initializes correctly."""
        adapter = DubboRemoteCallAdapter()
        assert adapter.supports_cross_service is True
        assert RemoteCallType.DUBBO in adapter.supported_call_types

    def test_supported_call_types(self) -> None:
        """Verify supported call types."""
        adapter = DubboRemoteCallAdapter()
        types = adapter.supported_call_types
        assert len(types) == 1
        assert types[0] == RemoteCallType.DUBBO

    def test_detect_remote_calls_file_not_found(self, tmp_path: Path) -> None:
        """Verify behavior when file not found."""
        adapter = DubboRemoteCallAdapter()
        calls = adapter.detect_remote_calls(str(tmp_path / "nonexistent.java"))
        assert calls == []

    def test_detect_remote_calls_empty_file(self, tmp_path: Path) -> None:
        """Verify behavior with empty file."""
        adapter = DubboRemoteCallAdapter()
        test_file = tmp_path / "Test.java"
        test_file.write_text("")

        calls = adapter.detect_remote_calls(str(test_file))
        assert calls == []

    def test_detect_dubbo_calls(self, tmp_path: Path) -> None:
        """Verify detection of Dubbo calls."""
        adapter = DubboRemoteCallAdapter()
        test_file = tmp_path / "Service.java"
        test_file.write_text("""
        @DubboReference
        private UserService userService;
        """)

        calls = adapter.detect_remote_calls(str(test_file))
        assert len(calls) == 1
        assert calls[0].call_type == RemoteCallType.DUBBO


class TestFeignRemoteCallAdapter:
    """Tests for FeignRemoteCallAdapter."""

    def test_adapter_initialization(self) -> None:
        """Verify adapter initializes correctly."""
        adapter = FeignRemoteCallAdapter()
        assert adapter.supports_cross_service is True
        assert RemoteCallType.FEIGN in adapter.supported_call_types

    def test_supported_call_types(self) -> None:
        """Verify supported call types."""
        adapter = FeignRemoteCallAdapter()
        types = adapter.supported_call_types
        assert len(types) == 1
        assert types[0] == RemoteCallType.FEIGN

    def test_detect_feign_calls(self, tmp_path: Path) -> None:
        """Verify detection of Feign calls."""
        adapter = FeignRemoteCallAdapter()
        test_file = tmp_path / "Client.java"
        test_file.write_text("""
        @FeignClient(name = "user-service", url = "http://user-service")
        public interface UserClient {}
        """)

        calls = adapter.detect_remote_calls(str(test_file))
        assert len(calls) == 1
        assert calls[0].call_type == RemoteCallType.FEIGN


class TestHttpRemoteCallAdapter:
    """Tests for HttpRemoteCallAdapter."""

    def test_adapter_initialization(self) -> None:
        """Verify adapter initializes correctly."""
        adapter = HttpRemoteCallAdapter()
        assert adapter.supports_cross_service is True
        assert RemoteCallType.REST in adapter.supported_call_types

    def test_supported_call_types(self) -> None:
        """Verify supported call types."""
        adapter = HttpRemoteCallAdapter()
        types = adapter.supported_call_types
        assert len(types) == 1
        assert types[0] == RemoteCallType.REST

    def test_detect_http_calls(self, tmp_path: Path) -> None:
        """Verify detection of HTTP calls."""
        adapter = HttpRemoteCallAdapter()
        test_file = tmp_path / "ApiService.java"
        test_file.write_text("""
        restTemplate.getForObject("http://api/users", String.class);
        """)

        calls = adapter.detect_remote_calls(str(test_file))
        assert len(calls) >= 1
        assert all(c.call_type == RemoteCallType.REST for c in calls)


class TestMessageQueueRemoteCallAdapter:
    """Tests for MessageQueueRemoteCallAdapter."""

    def test_adapter_initialization(self) -> None:
        """Verify adapter initializes correctly."""
        adapter = MessageQueueRemoteCallAdapter()
        assert adapter.supports_cross_service is True
        assert RemoteCallType.MQ_RABBITMQ in adapter.supported_call_types
        assert RemoteCallType.MQ_KAFKA in adapter.supported_call_types
        assert RemoteCallType.MQ_ROCKETMQ in adapter.supported_call_types

    def test_supported_call_types(self) -> None:
        """Verify supported call types."""
        adapter = MessageQueueRemoteCallAdapter()
        types = adapter.supported_call_types
        assert len(types) == 3
        assert RemoteCallType.MQ_RABBITMQ in types
        assert RemoteCallType.MQ_KAFKA in types
        assert RemoteCallType.MQ_ROCKETMQ in types

    def test_detect_mq_calls(self, tmp_path: Path) -> None:
        """Verify detection of MQ calls."""
        adapter = MessageQueueRemoteCallAdapter()
        test_file = tmp_path / "Consumer.java"
        test_file.write_text("""
        @RabbitListener(queues = "order.queue")
        public void processOrder(Order order) {}

        @KafkaListener(topics = "user-events")
        public void handleUser(UserEvent event) {}
        """)

        calls = adapter.detect_remote_calls(str(test_file))
        assert len(calls) == 2
        call_types = {c.call_type for c in calls}
        assert RemoteCallType.MQ_RABBITMQ in call_types
        assert RemoteCallType.MQ_KAFKA in call_types

    def test_get_calls_by_broker(self) -> None:
        """Verify grouping by broker type."""
        adapter = MessageQueueRemoteCallAdapter()
        from jcia.core.entities.remote_call import RemoteCallInfo, RemoteEndpoint

        calls = [
            RemoteCallInfo(
                call_type=RemoteCallType.MQ_RABBITMQ,
                endpoint=RemoteEndpoint(url="queue1"),
                caller_class="A",
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.MQ_KAFKA,
                endpoint=RemoteEndpoint(url="topic1"),
                caller_class="B",
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.MQ_RABBITMQ,
                endpoint=RemoteEndpoint(url="queue2"),
                caller_class="C",
            ),
        ]

        grouped = adapter.get_calls_by_broker(calls)
        assert len(grouped[RemoteCallType.MQ_RABBITMQ]) == 2
        assert len(grouped[RemoteCallType.MQ_KAFKA]) == 1


class TestCompositeRemoteCallAdapter:
    """Tests for CompositeRemoteCallAdapter."""

    def test_adapter_initialization(self) -> None:
        """Verify adapter initializes correctly."""
        adapter = CompositeRemoteCallAdapter()
        assert adapter.supports_cross_service is True
        assert len(adapter.supported_call_types) >= 5

    def test_supported_call_types_includes_all(self) -> None:
        """Verify all call types are supported."""
        adapter = CompositeRemoteCallAdapter()
        types = adapter.supported_call_types

        assert RemoteCallType.DUBBO in types
        assert RemoteCallType.FEIGN in types
        assert RemoteCallType.REST in types
        assert RemoteCallType.MQ_RABBITMQ in types
        assert RemoteCallType.MQ_KAFKA in types
        assert RemoteCallType.MQ_ROCKETMQ in types

    def test_detect_all_remote_calls(self, tmp_path: Path) -> None:
        """Verify detection of all remote call types."""
        adapter = CompositeRemoteCallAdapter()
        test_file = tmp_path / "MixedService.java"
        test_file.write_text("""
        @DubboReference
        private UserService userService;

        @FeignClient(name = "order-service")
        interface OrderClient {}

        restTemplate.getForObject("http://api/test", String.class);

        @RabbitListener(queues = "events")
        void handleEvent(Event e) {}
        """)

        calls = adapter.detect_remote_calls(str(test_file))
        assert len(calls) >= 3

        call_types = {c.call_type for c in calls}
        assert RemoteCallType.DUBBO in call_types
        assert RemoteCallType.FEIGN in call_types
        assert RemoteCallType.MQ_RABBITMQ in call_types

    def test_get_calls_by_type(self) -> None:
        """Verify grouping by call type."""
        adapter = CompositeRemoteCallAdapter()
        from jcia.core.entities.remote_call import RemoteCallInfo, RemoteEndpoint

        calls = [
            RemoteCallInfo(
                call_type=RemoteCallType.DUBBO,
                endpoint=RemoteEndpoint(service_name="svc1"),
                caller_class="A",
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.FEIGN,
                endpoint=RemoteEndpoint(service_name="svc2"),
                caller_class="B",
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.DUBBO,
                endpoint=RemoteEndpoint(service_name="svc3"),
                caller_class="C",
            ),
        ]

        grouped = adapter.get_calls_by_type(calls)
        assert len(grouped[RemoteCallType.DUBBO]) == 2
        assert len(grouped[RemoteCallType.FEIGN]) == 1

    def test_get_statistics(self) -> None:
        """Verify statistics calculation."""
        adapter = CompositeRemoteCallAdapter()
        from jcia.core.entities.remote_call import RemoteCallInfo, RemoteEndpoint

        calls = [
            RemoteCallInfo(
                call_type=RemoteCallType.DUBBO,
                endpoint=RemoteEndpoint(service_name="svc1"),
                caller_class="A",
                confidence=0.95,
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.FEIGN,
                endpoint=RemoteEndpoint(service_name="svc2"),
                caller_class="B",
                confidence=0.8,
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.MQ_KAFKA,
                endpoint=RemoteEndpoint(url="topic1"),
                caller_class="C",
                confidence=0.9,
            ),
        ]

        stats = adapter.get_statistics(calls)
        assert stats["total"] == 3
        assert stats["rpc"] == 2  # DUBBO + FEIGN
        assert stats["mq"] == 1  # KAFKA
        assert stats["high_confidence"] == 2  # >= 0.9

    def test_detect_from_directory(self, tmp_path: Path) -> None:
        """Verify detection from directory."""
        adapter = CompositeRemoteCallAdapter()

        # Create multiple Java files
        (tmp_path / "Service1.java").write_text("""
        @DubboReference
        private UserService userService;
        """)
        (tmp_path / "Service2.java").write_text("""
        @FeignClient(name = "order-service")
        interface OrderClient {}
        """)

        calls = adapter.detect_from_directory(tmp_path)
        assert len(calls) >= 2

        call_types = {c.call_type for c in calls}
        assert RemoteCallType.DUBBO in call_types
        assert RemoteCallType.FEIGN in call_types