"""Remote call analyzer abstract interface.

This module defines the abstract interface for remote call detection and analysis,
supporting RPC calls (Dubbo, Feign, gRPC, REST) and message queue interactions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jcia.core.entities.remote_call import RemoteCallInfo, RemoteCallType, RemoteCallChain


@dataclass
class RemoteCallAnalysisResult:
    """Result of remote call analysis for a single source file.

    Attributes:
        source_file: Path to the analyzed source file
        calls: List of detected remote calls
        total_calls: Total number of calls detected
        rpc_calls: Number of RPC-type calls
        mq_calls: Number of message queue calls
        high_confidence_count: Number of calls with confidence >= 0.9
    """

    source_file: str
    calls: list["RemoteCallInfo"] = field(default_factory=list)
    total_calls: int = 0
    rpc_calls: int = 0
    mq_calls: int = 0
    high_confidence_count: int = 0

    def __post_init__(self) -> None:
        """Calculate statistics from calls."""
        self._calculate_stats()

    def _calculate_stats(self) -> None:
        """Calculate statistics from the calls list."""
        self.total_calls = len(self.calls)
        self.rpc_calls = sum(1 for c in self.calls if c.call_type.is_rpc())
        self.mq_calls = sum(1 for c in self.calls if c.call_type.is_message_queue())
        self.high_confidence_count = sum(1 for c in self.calls if c.is_high_confidence())

    def get_calls_by_type(self, call_type: "RemoteCallType") -> list["RemoteCallInfo"]:
        """Filter calls by type.

        Args:
            call_type: The type of call to filter

        Returns:
            List of calls matching the specified type
        """
        return [c for c in self.calls if c.call_type == call_type]


class RemoteCallAnalyzer(ABC):
    """Abstract interface for remote call detection and analysis.

    Analyzers detect remote calls in Java source code and analyze
    cross-service call chains for impact analysis in microservices.

    Example:
        ```python
        analyzer = DubboAdapter()
        calls = analyzer.detect_remote_calls("Service.java")
        for call in calls:
            print(f"Found {call.call_type}: {call.endpoint.service_name}")
        ```
    """

    @abstractmethod
    def detect_remote_calls(self, source_path: str) -> list["RemoteCallInfo"]:
        """Detect remote calls in a source file.

        Args:
            source_path: Path to the Java source file

        Returns:
            List of detected remote call information
        """
        pass

    @abstractmethod
    def analyze_cross_service_chain(
        self, method: str, max_hops: int = 5
    ) -> list["RemoteCallChain"]:
        """Analyze cross-service call chain from a method.

        Traces remote calls across service boundaries up to max_hops.

        Args:
            method: Starting method (fully qualified name)
            max_hops: Maximum number of service boundary crossings

        Returns:
            List of cross-service call chains
        """
        pass

    @property
    @abstractmethod
    def supported_call_types(self) -> list["RemoteCallType"]:
        """Get supported call types for this analyzer.

        Returns:
            List of RemoteCallType enums this analyzer can detect
        """
        pass

    @property
    @abstractmethod
    def supports_cross_service(self) -> bool:
        """Check if analyzer supports cross-service analysis.

        Returns:
            True if analyzer can trace calls across service boundaries
        """
        pass