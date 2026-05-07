"""Remote call detection service.

This module provides a domain service for detecting and analyzing remote calls
in Java microservices architectures.
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jcia.adapters.tools.remote_call.composite_adapter import CompositeRemoteCallAdapter

from jcia.core.entities.remote_call import (
    RemoteCallChain,
    RemoteCallInfo,
    RemoteCallType,
)

logger = logging.getLogger(__name__)


@dataclass
class RemoteCallDetectionResult:
    """Result of remote call detection for a file or directory.

    Attributes:
        file_path: Path to the analyzed file
        calls: List of detected remote calls
        analysis_time_ms: Time taken for analysis in milliseconds
        error: Error message if analysis failed
    """

    file_path: str
    calls: list[RemoteCallInfo] = field(default_factory=list)
    analysis_time_ms: float = 0.0
    error: str | None = None

    def get_statistics(self) -> dict[str, int | float]:
        """Get statistics about detected calls.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_calls": len(self.calls),
            "rpc_calls": sum(1 for c in self.calls if c.call_type.is_rpc()),
            "mq_calls": sum(1 for c in self.calls if c.call_type.is_message_queue()),
            "high_confidence": sum(1 for c in self.calls if c.is_high_confidence()),
            "analysis_time_ms": self.analysis_time_ms,
        }


class RemoteCallDetectionService:
    """Service for detecting and analyzing remote calls.

    Provides high-level operations for detecting remote calls,
    filtering results, and analyzing cross-service call chains.

    Example:
        ```python
        service = RemoteCallDetectionService()
        result = service.detect_from_file("OrderService.java")
        for call in result.calls:
            print(f"{call.call_type}: {call.endpoint.service_name}")
        ```
    """

    def __init__(self) -> None:
        """Initialize the detection service."""
        from jcia.adapters.tools.remote_call.composite_adapter import CompositeRemoteCallAdapter

        self._adapter: CompositeRemoteCallAdapter = CompositeRemoteCallAdapter()

    def detect_from_file(self, file_path: str) -> RemoteCallDetectionResult:
        """Detect remote calls from a single file.

        Args:
            file_path: Path to the Java source file

        Returns:
            RemoteCallDetectionResult with detected calls
        """
        start_time = time.time()

        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                return RemoteCallDetectionResult(
                    file_path=file_path,
                    error="File not found",
                )

            calls = self._adapter.detect_remote_calls(file_path)
            elapsed_ms = (time.time() - start_time) * 1000

            return RemoteCallDetectionResult(
                file_path=file_path,
                calls=calls,
                analysis_time_ms=elapsed_ms,
            )

        except Exception as e:
            logger.error(f"Error detecting remote calls in {file_path}: {e}")
            elapsed_ms = (time.time() - start_time) * 1000
            return RemoteCallDetectionResult(
                file_path=file_path,
                error=str(e),
                analysis_time_ms=elapsed_ms,
            )

    def detect_from_directory(self, directory: Path) -> list[RemoteCallDetectionResult]:
        """Detect remote calls from all Java files in a directory.

        Args:
            directory: Path to the source directory

        Returns:
            List of detection results, one per file with calls
        """
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return []

        results: list[RemoteCallDetectionResult] = []

        for java_file in directory.rglob("*.java"):
            result = self.detect_from_file(str(java_file))
            if result.calls or result.error:
                results.append(result)

        logger.info(
            f"Analyzed {len(results)} files, "
            f"found {sum(len(r.calls) for r in results)} remote calls"
        )
        return results

    def filter_by_type(
        self, calls: list[RemoteCallInfo], types: list[RemoteCallType]
    ) -> list[RemoteCallInfo]:
        """Filter calls by call type.

        Args:
            calls: List of remote calls
            types: Types to include

        Returns:
            Filtered list of calls
        """
        type_set = set(types)
        return [c for c in calls if c.call_type in type_set]

    def filter_high_confidence(self, calls: list[RemoteCallInfo]) -> list[RemoteCallInfo]:
        """Filter for high confidence calls only.

        Args:
            calls: List of remote calls

        Returns:
            List of calls with confidence >= 0.9
        """
        return [c for c in calls if c.is_high_confidence()]

    def filter_by_confidence(
        self, calls: list[RemoteCallInfo], min_confidence: float
    ) -> list[RemoteCallInfo]:
        """Filter calls by minimum confidence.

        Args:
            calls: List of remote calls
            min_confidence: Minimum confidence threshold

        Returns:
            Filtered list of calls
        """
        return [c for c in calls if c.confidence >= min_confidence]

    def get_unique_services(self, calls: list[RemoteCallInfo]) -> set[str]:
        """Extract unique service names from calls.

        Args:
            calls: List of remote calls

        Returns:
            Set of unique service names
        """
        services: set[str] = set()
        for call in calls:
            if call.endpoint.service_name:
                services.add(call.endpoint.service_name)
        return services

    def build_call_chains(
        self, calls: list[RemoteCallInfo], max_depth: int = 5
    ) -> list[RemoteCallChain]:
        """Build cross-service call chains from detected calls.

        This is a basic implementation that requires service registry
        integration for full cross-service chain analysis.

        Args:
            calls: List of remote calls
            max_depth: Maximum chain depth

        Returns:
            List of call chains
        """
        # Basic implementation - would need service registry for full analysis
        # Group calls by source class and build chains
        chains: list[RemoteCallChain] = []

        # Group by caller class
        calls_by_caller: dict[str, list[RemoteCallInfo]] = {}
        for call in calls:
            caller = call.caller_class
            if caller not in calls_by_caller:
                calls_by_caller[caller] = []
            calls_by_caller[caller].append(call)

        # Build simple chains
        for caller_class, caller_calls in calls_by_caller.items():
            if len(caller_calls) >= 1:
                # Create a chain starting from this class
                chain = RemoteCallChain(
                    calls=caller_calls,
                    source_method=f"{caller_class}.unknown",
                    target_service=caller_calls[-1].endpoint.service_name,
                )
                chain.total_confidence = chain.calculate_total_confidence()
                chains.append(chain)

        return chains

    def get_detection_summary(self, result: RemoteCallDetectionResult) -> dict[str, int | float | str]:
        """Get a summary of detection results.

        Args:
            result: Detection result

        Returns:
            Dictionary with summary information
        """
        stats = result.get_statistics()
        stats["file_path"] = result.file_path
        if result.error:
            stats["error"] = result.error
        return stats

    def aggregate_results(
        self, results: list[RemoteCallDetectionResult]
    ) -> dict[str, int | float]:
        """Aggregate statistics from multiple results.

        Args:
            results: List of detection results

        Returns:
            Aggregated statistics
        """
        all_calls: list[RemoteCallInfo] = []
        total_time = 0.0
        error_count = 0

        for result in results:
            all_calls.extend(result.calls)
            total_time += result.analysis_time_ms
            if result.error:
                error_count += 1

        return {
            "total_files": len(results),
            "total_calls": len(all_calls),
            "rpc_calls": sum(1 for c in all_calls if c.call_type.is_rpc()),
            "mq_calls": sum(1 for c in all_calls if c.call_type.is_message_queue()),
            "high_confidence": sum(1 for c in all_calls if c.is_high_confidence()),
            "total_analysis_time_ms": total_time,
            "unique_services": len(self.get_unique_services(all_calls)),
            "error_count": error_count,
        }