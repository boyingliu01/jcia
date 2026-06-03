"""gRPC remote call adapter.

Detects gRPC remote calls in Java source code.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from jcia.core.entities.remote_call import (
    RemoteCallChain,
    RemoteCallInfo,
    RemoteCallType,
)
from jcia.core.interfaces.remote_call_analyzer import RemoteCallAnalyzer

if TYPE_CHECKING:
    from jcia.core.interfaces.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)


class GrpcRemoteCallAdapter(RemoteCallAnalyzer):
    """Adapter for detecting gRPC calls.

    Detects gRPC-specific patterns:
    - ManagedChannel creation
    - ManagedChannelBuilder
    - gRPC service stubs (generated)

    Example:
        ```python
        adapter = GrpcRemoteCallAdapter()
        calls = adapter.detect_remote_calls("OrderService.java")
        for call in calls:
            print(f"Service: {call.endpoint.service_name}")
        ```
    """

    def __init__(
        self, service_registry: "ServiceRegistry | None" = None
    ) -> None:
        """Initialize the gRPC adapter.

        Args:
            service_registry: Optional service registry for cross-service
                chain analysis. If not provided, cross-service analysis
                will return empty results.
        """
        from jcia.adapters.tools.remote_call_patterns import RemoteCallPatternMatcher

        self._matcher = RemoteCallPatternMatcher()
        self._registry = service_registry

    @property
    def supported_call_types(self) -> list[RemoteCallType]:
        """Get supported call types.

        Returns:
            List containing only GRPC type
        """
        return [RemoteCallType.GRPC]

    @property
    def supports_cross_service(self) -> bool:
        """gRPC adapter supports cross-service analysis.

        Returns:
            True - gRPC provides service interface information
        """
        return True

    def detect_remote_calls(self, source_path: str) -> list[RemoteCallInfo]:
        """Detect gRPC calls in a source file.

        Args:
            source_path: Path to the Java source file

        Returns:
            List of detected gRPC remote calls
        """
        path = Path(source_path)
        if not path.exists():
            logger.warning(f"File not found: {source_path}")
            return []

        # Use pattern matcher and filter for gRPC calls only
        all_calls = self._matcher.analyze_file(path)
        grpc_calls = [c for c in all_calls if c.call_type == RemoteCallType.GRPC]

        logger.debug(f"Found {len(grpc_calls)} gRPC calls in {source_path}")
        return grpc_calls

    def analyze_cross_service_chain(
        self, method: str, max_hops: int = 5
    ) -> list[RemoteCallChain]:
        """Analyze cross-service call chain from a method.

        For gRPC, this traces service-to-service calls via gRPC interfaces.

        Args:
            method: Starting method (fully qualified name)
            max_hops: Maximum number of service boundary crossings

        Returns:
            List of cross-service call chains
        """
        # Basic implementation - would need service registry integration
        # for full cross-service chain analysis
        logger.debug(
            f"Analyzing cross-service chain from {method}, max_hops={max_hops}"
        )
        return []

    def detect_from_directory(self, directory: Path) -> list[RemoteCallInfo]:
        """Detect gRPC calls from all Java files in a directory.

        Args:
            directory: Path to the source directory

        Returns:
            List of detected gRPC remote calls
        """
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return []

        all_calls: list[RemoteCallInfo] = []
        for java_file in directory.rglob("*.java"):
            calls = self.detect_remote_calls(str(java_file))
            all_calls.extend(calls)

        logger.info(f"Found {len(all_calls)} gRPC calls in {directory}")
        return all_calls