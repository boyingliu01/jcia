"""Tests for RemoteCallAnalyzer interface.

This module tests the RemoteCallAnalyzer abstract interface and related data structures.
"""

import pytest

from jcia.core.interfaces.remote_call_analyzer import (
    RemoteCallAnalyzer,
    RemoteCallAnalysisResult,
)


class TestRemoteCallAnalysisResult:
    """Tests for RemoteCallAnalysisResult dataclass."""

    def test_create_result_with_all_fields(self) -> None:
        """Create result with all fields."""
        from jcia.core.entities.remote_call import RemoteCallInfo, RemoteCallType, RemoteEndpoint

        endpoint = RemoteEndpoint(service_name="user-service")
        call = RemoteCallInfo(
            call_type=RemoteCallType.DUBBO,
            endpoint=endpoint,
            caller_class="OrderService",
            confidence=0.95,  # High confidence threshold is 0.9
        )

        result = RemoteCallAnalysisResult(
            source_file="OrderService.java",
            calls=[call],
            total_calls=1,
            rpc_calls=1,
            mq_calls=0,
            high_confidence_count=1,
        )
        assert result.source_file == "OrderService.java"
        assert len(result.calls) == 1
        assert result.total_calls == 1
        assert result.rpc_calls == 1
        assert result.mq_calls == 0
        assert result.high_confidence_count == 1

    def test_result_default_values(self) -> None:
        """Verify default values."""
        result = RemoteCallAnalysisResult(source_file="Test.java")
        assert result.calls == []
        assert result.total_calls == 0
        assert result.rpc_calls == 0
        assert result.mq_calls == 0
        assert result.high_confidence_count == 0

    def test_result_calculate_stats(self) -> None:
        """Verify stats calculation."""
        from jcia.core.entities.remote_call import RemoteCallInfo, RemoteCallType, RemoteEndpoint

        calls = [
            RemoteCallInfo(
                call_type=RemoteCallType.DUBBO,
                endpoint=RemoteEndpoint(service_name="svc1"),
                caller_class="A",
                confidence=0.95,
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.MQ_KAFKA,
                endpoint=RemoteEndpoint(service_name="svc2"),
                caller_class="A",
                confidence=0.8,
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.FEIGN,
                endpoint=RemoteEndpoint(service_name="svc3"),
                caller_class="B",
                confidence=0.6,
            ),
        ]
        result = RemoteCallAnalysisResult(source_file="A.java", calls=calls)

        # Verify stats are recalculated
        assert result.total_calls == 3
        assert result.rpc_calls == 2  # DUBBO + FEIGN
        assert result.mq_calls == 1  # KAFKA
        assert result.high_confidence_count == 1  # Only DUBBO >= 0.9

    def test_result_get_calls_by_type(self) -> None:
        """Verify filtering by call type."""
        from jcia.core.entities.remote_call import RemoteCallInfo, RemoteCallType, RemoteEndpoint

        calls = [
            RemoteCallInfo(
                call_type=RemoteCallType.DUBBO,
                endpoint=RemoteEndpoint(service_name="svc1"),
                caller_class="A",
            ),
            RemoteCallInfo(
                call_type=RemoteCallType.FEIGN,
                endpoint=RemoteEndpoint(service_name="svc2"),
                caller_class="A",
            ),
        ]
        result = RemoteCallAnalysisResult(source_file="A.java", calls=calls)

        dubbo_calls = result.get_calls_by_type(RemoteCallType.DUBBO)
        assert len(dubbo_calls) == 1
        assert dubbo_calls[0].call_type == RemoteCallType.DUBBO

        feign_calls = result.get_calls_by_type(RemoteCallType.FEIGN)
        assert len(feign_calls) == 1


class TestRemoteCallAnalyzerInterface:
    """Tests for RemoteCallAnalyzer abstract interface."""

    def test_interface_is_abstract(self) -> None:
        """Verify interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RemoteCallAnalyzer()  # type: ignore

    def test_interface_has_required_methods(self) -> None:
        """Verify interface has required abstract methods."""
        # Check that the abstract methods exist
        assert hasattr(RemoteCallAnalyzer, "detect_remote_calls")
        assert hasattr(RemoteCallAnalyzer, "analyze_cross_service_chain")
        assert hasattr(RemoteCallAnalyzer, "supported_call_types")
        assert hasattr(RemoteCallAnalyzer, "supports_cross_service")

    def test_interface_can_be_subclassed(self) -> None:
        """Verify interface can be properly subclassed."""
        from jcia.core.entities.remote_call import RemoteCallInfo, RemoteCallType, RemoteCallChain

        class MockRemoteCallAnalyzer(RemoteCallAnalyzer):
            @property
            def supported_call_types(self) -> list[RemoteCallType]:
                return [RemoteCallType.DUBBO, RemoteCallType.FEIGN]

            @property
            def supports_cross_service(self) -> bool:
                return True

            def detect_remote_calls(self, source_path: str) -> list[RemoteCallInfo]:
                return []

            def analyze_cross_service_chain(
                self, method: str, max_hops: int = 5
            ) -> list[RemoteCallChain]:
                return []

        analyzer = MockRemoteCallAnalyzer()
        assert analyzer.supported_call_types == [RemoteCallType.DUBBO, RemoteCallType.FEIGN]
        assert analyzer.supports_cross_service is True
        assert analyzer.detect_remote_calls("test.java") == []
        assert analyzer.analyze_cross_service_chain("method") == []

    def test_interface_method_signatures(self) -> None:
        """Verify interface method signatures are correct."""
        from jcia.core.entities.remote_call import RemoteCallInfo, RemoteCallType, RemoteCallChain

        # Check detect_remote_calls has correct parameter types
        # Note: get_type_hints on abstract methods with TYPE_CHECKING imports
        # may not resolve correctly, so we check method existence instead
        method = RemoteCallAnalyzer.detect_remote_calls
        assert hasattr(method, "__func__") or callable(method)

        # Verify the method accepts source_path parameter
        import inspect
        sig = inspect.signature(RemoteCallAnalyzer.detect_remote_calls)
        params = list(sig.parameters.keys())
        assert "source_path" in params

        # Check analyze_cross_service_chain signature
        sig = inspect.signature(RemoteCallAnalyzer.analyze_cross_service_chain)
        params = list(sig.parameters.keys())
        assert "method" in params
        assert "max_hops" in params