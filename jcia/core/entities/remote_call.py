"""Remote call information entities for cross-service communication analysis.

This module provides data models for representing remote calls detected in Java
microservices architectures, including RPC calls (Dubbo, Feign, gRPC, REST) and
message queue interactions (RabbitMQ, Kafka, RocketMQ).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RemoteCallType(Enum):
    """Types of remote calls in Java microservices.

    Attributes:
        DUBBO: Apache Dubbo RPC call
        FEIGN: Spring Cloud OpenFeign client
        GRPC: gRPC call
        REST: REST/HTTP client call
        MQ_RABBITMQ: RabbitMQ message queue
        MQ_KAFKA: Apache Kafka message queue
        MQ_ROCKETMQ: Apache RocketMQ message queue
    """

    DUBBO = "dubbo"
    FEIGN = "feign"
    GRPC = "grpc"
    REST = "rest"
    MQ_RABBITMQ = "rabbitmq"
    MQ_KAFKA = "kafka"
    MQ_ROCKETMQ = "rocketmq"

    def is_rpc(self) -> bool:
        """Check if this call type is an RPC call.

        Returns:
            True if the call type is RPC-based (Dubbo, Feign, gRPC, REST)
        """
        return self in (
            RemoteCallType.DUBBO,
            RemoteCallType.FEIGN,
            RemoteCallType.GRPC,
            RemoteCallType.REST,
        )

    def is_message_queue(self) -> bool:
        """Check if this call type is a message queue.

        Returns:
            True if the call type is message queue-based
        """
        return self in (
            RemoteCallType.MQ_RABBITMQ,
            RemoteCallType.MQ_KAFKA,
            RemoteCallType.MQ_ROCKETMQ,
        )


@dataclass
class RemoteEndpoint:
    """Remote service endpoint information.

    Represents the target of a remote call, including service name,
    interface, method, and connection details.

    Attributes:
        service_name: Target service name
        interface: Interface or API name
        method: Method name being called
        url: Full URL for REST calls
        version: Service version (Dubbo)
        group: Service group (Dubbo)
    """

    service_name: str | None = None
    interface: str | None = None
    method: str | None = None
    url: str | None = None
    version: str | None = None
    group: str | None = None

    @property
    def full_identifier(self) -> str:
        """Get full identifier string for the endpoint.

        Returns:
            Combined identifier string (service:interface.method)
        """
        parts: list[str] = []
        if self.service_name:
            parts.append(self.service_name)
        if self.interface:
            parts.append(self.interface)
        if self.method:
            if parts:
                parts[-1] = f"{parts[-1]}.{self.method}"
            else:
                parts.append(self.method)
        return ":".join(parts) if len(parts) > 1 else parts[0] if parts else ""

    def is_complete(self) -> bool:
        """Check if endpoint has complete information.

        Returns:
            True if service name and at least interface or method are set
        """
        return (
            self.service_name is not None
            and (self.interface is not None or self.method is not None)
        )


@dataclass
class RemoteCallInfo:
    """Information about a detected remote call.

    Represents a single remote call found in source code,
    including the call type, endpoint, caller context, and confidence.

    Attributes:
        call_type: Type of remote call (Dubbo, Feign, etc.)
        endpoint: Target endpoint information
        caller_class: Class containing the remote call
        caller_method: Method containing the remote call
        confidence: Detection confidence (0.0-1.0)
        source_line: Line number in source file
        source_file: Path to source file
        annotation: Annotation used for the call
        metadata: Additional metadata
    """

    call_type: RemoteCallType
    endpoint: RemoteEndpoint
    caller_class: str
    caller_method: str | None = None
    confidence: float = 0.8
    source_line: int = 0
    source_file: str = ""
    annotation: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Prevent pytest from collecting this as a test class
    __test__ = False

    def is_high_confidence(self) -> bool:
        """Check if this call has high confidence.

        Returns:
            True if confidence >= 0.9
        """
        return self.confidence >= 0.9

    @property
    def full_call_signature(self) -> str:
        """Get full call signature string.

        Returns:
            Signature in format: CallerClass.method -> service.endpointMethod
        """
        caller = f"{self.caller_class}.{self.caller_method}" if self.caller_method else self.caller_class
        target = self.endpoint.full_identifier
        return f"{caller} -> {target}"


@dataclass
class RemoteCallChain:
    """A chain of cross-service remote calls.

    Represents a sequence of remote calls that span multiple services,
    useful for tracing impact propagation across microservices boundaries.

    Attributes:
        calls: List of remote calls in sequence
        source_method: Starting method of the chain
        target_service: Final target service
        total_confidence: Combined confidence of all calls
    """

    calls: list[RemoteCallInfo]
    source_method: str
    target_service: str | None = None
    total_confidence: float = 0.0

    # Prevent pytest from collecting this as a test class
    __test__ = False

    def hop_count(self) -> int:
        """Get number of hops (services) in the chain.

        Returns:
            Number of remote calls in the chain
        """
        return len(self.calls)

    def get_unique_services(self) -> set[str]:
        """Get unique service names involved in the chain.

        Returns:
            Set of unique service names
        """
        services: set[str] = set()
        for call in self.calls:
            if call.endpoint.service_name:
                services.add(call.endpoint.service_name)
        return services

    def calculate_total_confidence(self) -> float:
        """Calculate total confidence of the chain.

        Uses average confidence of all calls in the chain.

        Returns:
            Average confidence (0.0-1.0)
        """
        if not self.calls:
            return 0.0
        total = sum(call.confidence for call in self.calls)
        return total / len(self.calls)