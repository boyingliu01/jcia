"""Extended tests for remote call adapters to improve coverage.

This module provides comprehensive tests for Dubbo, Feign, HTTP, MQ, and Composite adapters
to increase test coverage from ~60% to 90%+.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from jcia.adapters.tools.remote_call import (
    CompositeRemoteCallAdapter,
    DubboRemoteCallAdapter,
    FeignRemoteCallAdapter,
    HttpRemoteCallAdapter,
    MessageQueueRemoteCallAdapter,
)
from jcia.core.entities.remote_call import RemoteCallType



class TestDubboRemoteCallAdapterExtended:
    """Extended tests for DubboRemoteCallAdapter."""

    def test_detect_from_directory_not_exist(self) -> None:
        """Test detection from non-existent directory."""
        adapter = DubboRemoteCallAdapter()
        result = adapter.detect_from_directory(Path("/nonexistent/path"))
        assert result == []

    def test_detect_from_directory_empty(self, tmp_path: Path) -> None:
        """Test detection from empty directory."""
        adapter = DubboRemoteCallAdapter()
        result = adapter.detect_from_directory(tmp_path)
        assert result == []

    def test_detect_from_directory_with_java_files(self, tmp_path: Path) -> None:
        """Test detection from directory with Java files."""
        adapter = DubboRemoteCallAdapter()

        # Create a Java file with Dubbo annotation
        java_file = tmp_path / "TestService.java"
        java_file.write_text("""
        @DubboReference
        private UserService userService;
        """)

        result = adapter.detect_from_directory(tmp_path)
        assert len(result) == 1
        assert result[0].call_type == RemoteCallType.DUBBO

    def test_detect_from_directory_nested(self, tmp_path: Path) -> None:
        """Test detection from nested directory structure."""
        adapter = DubboRemoteCallAdapter()

        # Create nested structure
        nested_dir = tmp_path / "src" / "main" / "java"
        nested_dir.mkdir(parents=True)

        java_file = nested_dir / "Service.java"
        java_file.write_text("""
        @DubboReference
        private OrderService orderService;
        """)

        result = adapter.detect_from_directory(tmp_path)
        assert len(result) == 1


class TestFeignRemoteCallAdapterExtended:
    """Extended tests for FeignRemoteCallAdapter."""

    def test_detect_from_directory_not_exist(self) -> None:
        """Test detection from non-existent directory."""
        adapter = FeignRemoteCallAdapter()
        result = adapter.detect_from_directory(Path("/nonexistent"))
        assert result == []

    def test_detect_from_directory_with_feign_client(self, tmp_path: Path) -> None:
        """Test detection of FeignClient annotation."""
        adapter = FeignRemoteCallAdapter()

        java_file = tmp_path / "UserClient.java"
        java_file.write_text("""
        @FeignClient(name = "user-service")
        public interface UserClient {}
        """)

        result = adapter.detect_from_directory(tmp_path)
        assert len(result) == 1
        assert result[0].call_type == RemoteCallType.FEIGN
        assert result[0].endpoint.service_name == "user-service"


class TestHttpRemoteCallAdapterExtended:
    """Extended tests for HttpRemoteCallAdapter."""

    def test_detect_from_directory_not_exist(self) -> None:
        """Test detection from non-existent directory."""
        adapter = HttpRemoteCallAdapter()
        result = adapter.detect_from_directory(Path("/nonexistent"))
        assert result == []

    def test_detect_from_directory_with_rest_template(self, tmp_path: Path) -> None:
        """Test detection of RestTemplate calls."""
        adapter = HttpRemoteCallAdapter()

        java_file = tmp_path / "ApiService.java"
        java_file.write_text("""
        restTemplate.getForObject("http://api/users", String.class);
        """)

        result = adapter.detect_from_directory(tmp_path)
        assert len(result) >= 1
        assert all(r.call_type == RemoteCallType.REST for r in result)


class TestMessageQueueRemoteCallAdapterExtended:
    """Extended tests for MessageQueueRemoteCallAdapter."""

    def test_detect_from_directory_not_exist(self) -> None:
        """Test detection from non-existent directory."""
        adapter = MessageQueueRemoteCallAdapter()
        result = adapter.detect_from_directory(Path("/nonexistent"))
        assert result == []

    def test_detect_from_directory_with_rabbit_listener(self, tmp_path: Path) -> None:
        """Test detection of RabbitListener annotation."""
        adapter = MessageQueueRemoteCallAdapter()

        java_file = tmp_path / "OrderConsumer.java"
        java_file.write_text("""
        @RabbitListener(queues = "order.queue")
        public void processOrder(Order order) {}
        """)

        result = adapter.detect_from_directory(tmp_path)
        assert len(result) == 1
        assert result[0].call_type == RemoteCallType.MQ_RABBITMQ
        assert result[0].endpoint.url == "order.queue"

    def test_detect_from_directory_with_kafka_listener(self, tmp_path: Path) -> None:
        """Test detection of KafkaListener annotation."""
        adapter = MessageQueueRemoteCallAdapter()

        java_file = tmp_path / "UserConsumer.java"
        java_file.write_text("""
        @KafkaListener(topics = "user-events")
        public void handleUserEvent(UserEvent event) {}
        """)

        result = adapter.detect_from_directory(tmp_path)
        assert len(result) == 1
        assert result[0].call_type == RemoteCallType.MQ_KAFKA
        assert result[0].endpoint.url == "user-events"

    def test_detect_from_directory_multiple_mq_types(self, tmp_path: Path) -> None:
        """Test detection of multiple MQ types in same directory."""
        adapter = MessageQueueRemoteCallAdapter()

        # Create RabbitMQ consumer
        rabbit_file = tmp_path / "RabbitConsumer.java"
        rabbit_file.write_text("""
        @RabbitListener(queues = "queue1")
        public void handle1() {}
        """)

        # Create Kafka consumer
        kafka_file = tmp_path / "KafkaConsumer.java"
        kafka_file.write_text("""
        @KafkaListener(topics = "topic1")
        public void handle2() {}
        """)

        result = adapter.detect_from_directory(tmp_path)
        assert len(result) == 2

        call_types = [r.call_type for r in result]
        assert RemoteCallType.MQ_RABBITMQ in call_types
        assert RemoteCallType.MQ_KAFKA in call_types


class TestCompositeRemoteCallAdapterExtended:
    """Extended tests for CompositeRemoteCallAdapter."""

    def test_get_statistics_empty(self) -> None:
        """Test statistics with empty calls list."""
        adapter = CompositeRemoteCallAdapter()
        stats = adapter.get_statistics([])

        assert stats["total"] == 0
        assert stats["rpc"] == 0
        assert stats["mq"] == 0
        assert stats["high_confidence"] == 0

    def test_get_statistics_multiple_types(self) -> None:
        """Test statistics with multiple call types."""
        from jcia.core.entities.remote_call import RemoteCallInfo, RemoteEndpoint

        adapter = CompositeRemoteCallAdapter()

        calls = [
            RemoteCallInfo(
                call_type=RemoteCallType.DUBBO,
                endpoint=RemoteEndpoint(service_name="svc1"),
                caller_class="A",
                confidence=0.95
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.FEIGN,
                endpoint=RemoteEndpoint(service_name="svc2"),
                caller_class="B",
                confidence=0.80
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.MQ_KAFKA,
                endpoint=RemoteEndpoint(url="topic1"),
                caller_class="C",
                confidence=0.90
            ),
        ]

        stats = adapter.get_statistics(calls)

        assert stats["total"] == 3
        assert stats["dubbo"] == 1
        assert stats["feign"] == 1
        assert stats["kafka"] == 1
        assert stats["high_confidence"] == 2  # 0.95 and 0.90 >= 0.9



if __name__ == "__main__":
    pytest.main([__file__, "-v"])