"""Dubbo RPC remote call adapter.

Detects Apache Dubbo remote calls in Java source code.
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


class DubboRemoteCallAdapter(RemoteCallAnalyzer):
    """Adapter for detecting Apache Dubbo RPC calls.

    Detects Dubbo-specific annotations and configurations:
    - @DubboReference
    - @DubboService
    - @Reference (Alibaba Dubbo)

    Example:
        ```python
        adapter = DubboRemoteCallAdapter()
        calls = adapter.detect_remote_calls("OrderService.java")
        for call in calls:
            print(f"Service: {call.endpoint.service_name}")
        ```
    """

    def __init__(self) -> None:
        """Initialize the Dubbo adapter."""
        from jcia.adapters.tools.remote_call_patterns import RemoteCallPatternMatcher

        self._matcher = RemoteCallPatternMatcher()

    @property
    def supported_call_types(self) -> list[RemoteCallType]:
        """Get supported call types.

        Returns:
            List containing only DUBBO type
        """
        return [RemoteCallType.DUBBO]

    @property
    def supports_cross_service(self) -> bool:
        """Dubbo adapter supports cross-service analysis.

        Returns:
            True - Dubbo provides service interface information
        """
        return True

    def detect_remote_calls(self, source_path: str) -> list[RemoteCallInfo]:
        """Detect Dubbo calls in a source file.

        Args:
            source_path: Path to the Java source file

        Returns:
            List of detected Dubbo remote calls
        """
        path = Path(source_path)
        if not path.exists():
            logger.warning(f"File not found: {source_path}")
            return []

        # Use pattern matcher and filter for Dubbo calls only
        all_calls = self._matcher.analyze_file(path)
        dubbo_calls = [c for c in all_calls if c.call_type == RemoteCallType.DUBBO]

        logger.debug(f"Found {len(dubbo_calls)} Dubbo calls in {source_path}")
        return dubbo_calls

    def analyze_cross_service_chain(
        self, method: str, max_hops: int = 5
    ) -> list[RemoteCallChain]:
        """Analyze cross-service call chain from a method.

        For Dubbo, this traces service-to-service calls via Dubbo interfaces.

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
        """Detect Dubbo calls from all Java files in a directory.

        Args:
            directory: Path to the source directory

        Returns:
            List of detected Dubbo remote calls
        """
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return []

        all_calls: list[RemoteCallInfo] = []
        for java_file in directory.rglob("*.java"):
            calls = self.detect_remote_calls(str(java_file))
            all_calls.extend(calls)

        logger.info(f"Found {len(all_calls)} Dubbo calls in {directory}")
        return all_calls