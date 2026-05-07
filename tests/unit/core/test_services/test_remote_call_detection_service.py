"""Tests for RemoteCallDetectionService.

This module tests the remote call detection service.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from jcia.core.services.remote_call_detection_service import (
    RemoteCallDetectionService,
    RemoteCallDetectionResult,
)
from jcia.core.entities.remote_call import (
    RemoteCallInfo,
    RemoteCallType,
    RemoteEndpoint,
    RemoteCallChain,
)


class TestRemoteCallDetectionResult:
    """Tests for RemoteCallDetectionResult."""

    def test_create_result(self) -> None:
        """Create detection result."""
        endpoint = RemoteEndpoint(service_name="user-service")
        call = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="OrderService",
        )
        result = RemoteCallDetectionResult(
            file_path="OrderService.java",
            calls=[call],
            analysis_time_ms=10.5,
        )
        assert result.file_path == "OrderService.java"
        assert len(result.calls) == 1
        assert pytest.approx(result.analysis_time_ms, rel=1e-9) == 10.5

    def test_result_default_values(self) -> None:
        """Verify default values."""
        result = RemoteCallDetectionResult(file_path="Test.java")
        assert result.calls == []
        assert result.analysis_time_ms == 0.0

    def test_result_statistics(self) -> None:
        """Verify statistics calculation."""
        calls = [
            RemoteCallInfo(
                call_type=RemoteCallType.DUBBO,
                endpoint=RemoteEndpoint(service_name="svc1"),
                caller_class="A",
                confidence=0.95,
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.MQ_KAFKA,
                endpoint=RemoteEndpoint(url="topic1"),
                caller_class="B",
                confidence=0.8,
            ),
        ]
        result = RemoteCallDetectionResult(file_path="Test.java", calls=calls)

        stats = result.get_statistics()
        assert stats["total_calls"] == 2
        assert stats["rpc_calls"] == 1
        assert stats["mq_calls"] == 1
        assert stats["high_confidence"] == 1


class TestRemoteCallDetectionService:
    """Tests for RemoteCallDetectionService."""

    def test_service_initialization(self) -> None:
        """Verify service initializes correctly."""
        service = RemoteCallDetectionService()
        assert service._adapter is not None

    def test_detect_from_file(self, tmp_path: Path) -> None:
        """Verify detection from single file."""
        test_file = tmp_path / "Service.java"
        test_file.write_text("""
        @DubboReference
        private UserService userService;
        """)

        service = RemoteCallDetectionService()
        result = service.detect_from_file(str(test_file))

        assert result.file_path == str(test_file)
        assert len(result.calls) >= 1

    def test_detect_from_directory(self, tmp_path: Path) -> None:
        """Verify detection from directory."""
        (tmp_path / "Service1.java").write_text("""
        @DubboReference
        private UserService userService;
        """)
        (tmp_path / "Service2.java").write_text("""
        @FeignClient(name = "order-service")
        interface OrderClient {}
        """)

        service = RemoteCallDetectionService()
        results = service.detect_from_directory(tmp_path)

        assert len(results) >= 1
        total_calls = sum(len(r.calls) for r in results)
        assert total_calls >= 2

    def test_detect_returns_empty_for_nonexistent_file(self) -> None:
        """Verify behavior for nonexistent file."""
        service = RemoteCallDetectionService()
        result = service.detect_from_file("/nonexistent/path/File.java")

        assert result.calls == []

    def test_filter_by_call_type(self) -> None:
        """Verify filtering by call type."""
        service = RemoteCallDetectionService()
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
                call_type=RemoteCallType.MQ_KAFKA,
                endpoint=RemoteEndpoint(url="topic"),
                caller_class="C",
            ),
        ]

        rpc_calls = service.filter_by_type(calls, [RemoteCallType.DUBBO, RemoteCallType.FEIGN])
        assert len(rpc_calls) == 2
        assert all(c.call_type.is_rpc() for c in rpc_calls)

    def test_filter_high_confidence(self) -> None:
        """Verify filtering high confidence calls."""
        service = RemoteCallDetectionService()
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
                confidence=0.7,
            ),
        ]

        high_conf = service.filter_high_confidence(calls)
        assert len(high_conf) == 1
        assert high_conf[0].confidence >= 0.9

    def test_get_unique_services(self) -> None:
        """Verify unique service extraction."""
        service = RemoteCallDetectionService()
        calls = [
            RemoteCallInfo(
                call_type=RemoteCallType.DUBBO,
                endpoint=RemoteEndpoint(service_name="user-service"),
                caller_class="A",
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.FEIGN,
                endpoint=RemoteEndpoint(service_name="order-service"),
                caller_class="B",
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.DUBBO,
                endpoint=RemoteEndpoint(service_name="user-service"),  # Duplicate
                caller_class="C",
            ),
        ]

        services = service.get_unique_services(calls)
        assert services == {"user-service", "order-service"}

    def test_build_call_chains(self) -> None:
        """Verify call chain building."""
        service = RemoteCallDetectionService()
        calls = [
            RemoteCallInfo(
                call_type=RemoteCallType.DUBBO,
                endpoint=RemoteEndpoint(service_name="svc1"),
                caller_class="OrderService",
                caller_method="createOrder",
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.FEIGN,
                endpoint=RemoteEndpoint(service_name="svc2"),
                caller_class="svc1",  # Simulates svc1 calling svc2
                caller_method="processPayment",
            ),
        ]

        chains = service.build_call_chains(calls, max_depth=3)
        # Basic implementation returns empty list without service registry
        assert isinstance(chains, list)

    def test_get_detection_summary(self, tmp_path: Path) -> None:
        """Verify detection summary."""
        (tmp_path / "Service.java").write_text("""
        @DubboReference
        private UserService userService;

        @FeignClient(name = "order-service")
        interface OrderClient {}
        """)

        service = RemoteCallDetectionService()
        result = service.detect_from_file(str(tmp_path / "Service.java"))
        summary = service.get_detection_summary(result)

        assert "total_calls" in summary
        assert summary["total_calls"] >= 1

    def test_detect_from_file_not_exist(self) -> None:
        """Test detection from non-existent file."""
        service = RemoteCallDetectionService()
        result = service.detect_from_file("/nonexistent/file.java")

        assert result.calls == []
        assert result.error == "File not found"

    def test_detect_from_directory_not_exist(self) -> None:
        """Test detection from non-existent directory."""
        service = RemoteCallDetectionService()
        results = service.detect_from_directory(Path("/nonexistent/directory"))

        assert results == []

    def test_filter_by_confidence(self) -> None:
        """Test filtering by confidence threshold."""
        service = RemoteCallDetectionService()
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
                confidence=0.7,
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.MQ_KAFKA,
                endpoint=RemoteEndpoint(url="topic"),
                caller_class="C",
                confidence=0.85,
            ),
        ]

        filtered = service.filter_by_confidence(calls, 0.8)
        assert len(filtered) == 2
        assert all(c.confidence >= 0.8 for c in filtered)

    def test_aggregate_results(self, tmp_path: Path) -> None:
        """Test aggregating multiple detection results."""
        service = RemoteCallDetectionService()

        (tmp_path / "Service1.java").write_text("""
        @DubboReference
        private UserService userService;
        """)
        (tmp_path / "Service2.java").write_text("""
        @FeignClient(name = "order-service")
        interface OrderClient {}
        """)

        # Create multiple results
        result1 = service.detect_from_file(str(tmp_path / "Service1.java"))
        result2 = service.detect_from_file(str(tmp_path / "Service2.java"))

        aggregated = service.aggregate_results([result1, result2])

        assert aggregated["total_files"] == 2
        assert aggregated["total_calls"] >= 2
        assert "rpc_calls" in aggregated
        assert "mq_calls" in aggregated
        assert "unique_services" in aggregated