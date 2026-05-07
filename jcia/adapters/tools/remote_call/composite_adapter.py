"""Composite remote call adapter.

Combines multiple remote call adapters for comprehensive detection.
"""

import logging
from pathlib import Path

from jcia.core.entities.remote_call import (
    RemoteCallChain,
    RemoteCallInfo,
    RemoteCallType,
)
from jcia.core.interfaces.remote_call_analyzer import RemoteCallAnalyzer

logger = logging.getLogger(__name__)


class CompositeRemoteCallAdapter(RemoteCallAnalyzer):
    """Composite adapter combining all remote call analyzers.

    Provides unified detection for all remote call types:
    - Dubbo RPC
    - Feign Client
    - HTTP Clients
    - Message Queues

    Example:
        ```python
        adapter = CompositeRemoteCallAdapter()
        calls = adapter.detect_remote_calls("Service.java")
        for call in calls:
            print(f"{call.call_type}: {call.endpoint.service_name}")
        ```
    """

    def __init__(self) -> None:
        """Initialize the composite adapter with all sub-adapters."""
        from jcia.adapters.tools.remote_call.dubbo_adapter import DubboRemoteCallAdapter
        from jcia.adapters.tools.remote_call.feign_adapter import FeignRemoteCallAdapter
        from jcia.adapters.tools.remote_call.http_adapter import HttpRemoteCallAdapter
        from jcia.adapters.tools.remote_call.mq_adapter import MessageQueueRemoteCallAdapter

        self._adapters: list[RemoteCallAnalyzer] = [
            DubboRemoteCallAdapter(),
            FeignRemoteCallAdapter(),
            HttpRemoteCallAdapter(),
            MessageQueueRemoteCallAdapter(),
        ]

    @property
    def supported_call_types(self) -> list[RemoteCallType]:
        """Get all supported call types.

        Returns:
            List of all supported RemoteCallType values
        """
        types: list[RemoteCallType] = []
        for adapter in self._adapters:
            types.extend(adapter.supported_call_types)
        return list(set(types))

    @property
    def supports_cross_service(self) -> bool:
        """Composite adapter supports cross-service analysis.

        Returns:
            True - all sub-adapters support cross-service
        """
        return all(adapter.supports_cross_service for adapter in self._adapters)

    def detect_remote_calls(self, source_path: str) -> list[RemoteCallInfo]:
        """Detect all remote calls in a source file.

        Combines results from all sub-adapters.

        Args:
            source_path: Path to the Java source file

        Returns:
            List of all detected remote calls
        """
        all_calls: list[RemoteCallInfo] = []

        for adapter in self._adapters:
            try:
                calls = adapter.detect_remote_calls(source_path)
                all_calls.extend(calls)
            except Exception as e:
                logger.warning(f"Adapter {adapter.__class__.__name__} failed: {e}")

        logger.debug(f"Found {len(all_calls)} total remote calls in {source_path}")
        return all_calls

    def analyze_cross_service_chain(
        self, method: str, max_hops: int = 5
    ) -> list[RemoteCallChain]:
        """Analyze cross-service call chain from a method.

        Combines chains from all sub-adapters.

        Args:
            method: Starting method (fully qualified name)
            max_hops: Maximum number of service boundary crossings

        Returns:
            List of cross-service call chains
        """
        all_chains: list[RemoteCallChain] = []

        for adapter in self._adapters:
            try:
                chains = adapter.analyze_cross_service_chain(method, max_hops)
                all_chains.extend(chains)
            except Exception as e:
                logger.warning(
                    f"Adapter {adapter.__class__.__name__} chain analysis failed: {e}"
                )

        return all_chains

    def detect_from_directory(self, directory: Path) -> list[RemoteCallInfo]:
        """Detect all remote calls from all Java files in a directory.

        Args:
            directory: Path to the source directory

        Returns:
            List of all detected remote calls
        """
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return []

        all_calls: list[RemoteCallInfo] = []
        for java_file in directory.rglob("*.java"):
            calls = self.detect_remote_calls(str(java_file))
            all_calls.extend(calls)

        logger.info(f"Found {len(all_calls)} remote calls in {directory}")
        return all_calls

    def get_calls_by_type(
        self, calls: list[RemoteCallInfo]
    ) -> dict[RemoteCallType, list[RemoteCallInfo]]:
        """Group calls by call type.

        Args:
            calls: List of remote calls

        Returns:
            Dictionary mapping call type to calls
        """
        grouped: dict[RemoteCallType, list[RemoteCallInfo]] = {}
        for call in calls:
            if call.call_type not in grouped:
                grouped[call.call_type] = []
            grouped[call.call_type].append(call)
        return grouped

    def get_statistics(self, calls: list[RemoteCallInfo]) -> dict[str, int]:
        """Get statistics about detected calls.

        Args:
            calls: List of remote calls

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total": len(calls),
            "rpc": sum(1 for c in calls if c.call_type.is_rpc()),
            "mq": sum(1 for c in calls if c.call_type.is_message_queue()),
            "high_confidence": sum(1 for c in calls if c.is_high_confidence()),
        }

        # Count by type
        for call_type in RemoteCallType:
            stats[call_type.value] = sum(1 for c in calls if c.call_type == call_type)

        return stats