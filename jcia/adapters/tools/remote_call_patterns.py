"""Remote call pattern matcher for Java source code.

This module provides pattern matching capabilities for detecting remote calls
in Java microservices code, including RPC (Dubbo, Feign, gRPC, REST) and
message queue (RabbitMQ, Kafka, RocketMQ) interactions.
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from jcia.core.entities.remote_call import (
    RemoteCallInfo,
    RemoteCallType,
    RemoteEndpoint,
)

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for remote call detection.

    Attributes:
        LITERAL: Direct string literal (0.95)
        ANNOTATION: Annotation without parameters (0.85)
        VARIABLE: Variable reference (0.60)
    """

    LITERAL = 0.95
    ANNOTATION = 0.85
    VARIABLE = 0.60


@dataclass
class RemoteCallPattern:
    """A remote call pattern definition.

    Attributes:
        call_type: Type of remote call
        regex: Compiled regex pattern
        confidence_base: Base confidence for this pattern type
        extractor: Function to extract endpoint info from match
    """

    call_type: RemoteCallType
    regex: re.Pattern[str]
    confidence_base: float
    extractor: Callable[[re.Match[str]], dict[str, Any]]


class RemoteCallPatternMatcher:
    """Matcher for remote call patterns in Java source code.

    Detects various remote call patterns including:
    - Dubbo RPC (@DubboReference, @DubboService)
    - Feign Client (@FeignClient)
    - HTTP Clients (RestTemplate, WebClient, OkHttpClient)
    - Message Queues (@RabbitListener, @KafkaListener, RocketMQ)
    - gRPC service stubs

    Example:
        ```python
        matcher = RemoteCallPatternMatcher()
        content = '@FeignClient(name = "user-service")'
        matches = matcher.find_patterns(content, "Client.java")
        for match in matches:
            print(f"Found {match.call_type}: {match.endpoint.service_name}")
        ```
    """

    def __init__(self) -> None:
        """Initialize the pattern matcher with all remote call patterns."""
        self._patterns = self._create_patterns()

    def _create_patterns(self) -> list[RemoteCallPattern]:
        """Create all remote call patterns.

        Returns:
            List of compiled remote call patterns
        """
        patterns: list[RemoteCallPattern] = []

        # Dubbo patterns
        patterns.extend(self._create_dubbo_patterns())

        # Feign patterns
        patterns.extend(self._create_feign_patterns())

        # HTTP client patterns
        patterns.extend(self._create_http_patterns())

        # Message queue patterns
        patterns.extend(self._create_mq_patterns())

        # gRPC patterns
        patterns.extend(self._create_grpc_patterns())

        return patterns

    def _create_dubbo_patterns(self) -> list[RemoteCallPattern]:
        """Create Dubbo RPC patterns."""
        patterns: list[RemoteCallPattern] = []

        # @DubboReference with parameters
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.DUBBO,
                regex=re.compile(
                    r"@DubboReference\s*\(\s*"
                    r"(?:interfaceClass\s*=\s*(\w+)\.class)?"
                    r"(?:\s*,?\s*version\s*=\s*\"([^\"]+)\"\s*)?"
                    r"(?:\s*,?\s*group\s*=\s*\"([^\"]+)\"\s*)?"
                    r"[^)]*\)",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.LITERAL.value,
                extractor=self._extract_dubbo_reference_params,
            )
        )

        # @DubboReference without parameters
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.DUBBO,
                regex=re.compile(
                    r"@DubboReference\s*(?:\(\s*\))?\s*\n?\s*(?:private|public)?\s+(\w+)\s+(\w+)",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.ANNOTATION.value,
                extractor=self._extract_dubbo_reference_simple,
            )
        )

        # @DubboService annotation
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.DUBBO,
                regex=re.compile(
                    r"@DubboService\s*\(\s*"
                    r"(?:version\s*=\s*\"([^\"]+)\"\s*)?"
                    r"(?:\s*,?\s*group\s*=\s*\"([^\"]+)\"\s*)?"
                    r"[^)]*\)",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.LITERAL.value,
                extractor=self._extract_dubbo_service,
            )
        )

        # @Reference (Alibaba Dubbo)
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.DUBBO,
                regex=re.compile(
                    r"@Reference\s*(?:\(\s*\))?\s*\n?\s*(?:private|public)?\s+\w+\s+(\w+)",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.ANNOTATION.value,
                extractor=self._extract_dubbo_reference_simple,
            )
        )

        return patterns

    def _create_feign_patterns(self) -> list[RemoteCallPattern]:
        """Create Feign Client patterns."""
        patterns: list[RemoteCallPattern] = []

        # @FeignClient with name or value
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.FEIGN,
                regex=re.compile(
                    r"@FeignClient\s*\(\s*"
                    r"(?:name|value)\s*=\s*\"([^\"]+)\""
                    r"(?:\s*,\s*url\s*=\s*\"([^\"]+)\"\s*)?"
                    r"[^)]*\)",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.LITERAL.value,
                extractor=self._extract_feign_client,
            )
        )

        return patterns

    def _create_http_patterns(self) -> list[RemoteCallPattern]:
        """Create HTTP client patterns."""
        patterns: list[RemoteCallPattern] = []

        # RestTemplate methods (getForObject, postForEntity, put, delete, exchange, etc.)
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.REST,
                regex=re.compile(
                    r"restTemplate\s*\.\s*(get\w*|post\w*|put\w*|delete\w*|exchange)\s*\(\s*\"([^\"]+)\"",
                    re.MULTILINE | re.IGNORECASE,
                ),
                confidence_base=ConfidenceLevel.LITERAL.value,
                extractor=self._extract_rest_template,
            )
        )

        # RestTemplate with variable URL
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.REST,
                regex=re.compile(
                    r"restTemplate\s*\.\s*(get\w*|post\w*|put\w*|delete\w*|exchange)\s*\(\s*([^,\"]+)",
                    re.MULTILINE | re.IGNORECASE,
                ),
                confidence_base=ConfidenceLevel.VARIABLE.value,
                extractor=self._extract_rest_template_variable,
            )
        )

        # WebClient methods
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.REST,
                regex=re.compile(
                    r"webClient\s*\.\s*(get|post|put|delete|method)\s*\(\s*\)",
                    re.MULTILINE | re.IGNORECASE,
                ),
                confidence_base=ConfidenceLevel.ANNOTATION.value,
                extractor=self._extract_web_client,
            )
        )

        # OkHttpClient
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.REST,
                regex=re.compile(
                    r"OkHttpClient|okhttp",
                    re.MULTILINE | re.IGNORECASE,
                ),
                confidence_base=ConfidenceLevel.ANNOTATION.value,
                extractor=self._extract_okhttp,
            )
        )

        return patterns

    def _create_mq_patterns(self) -> list[RemoteCallPattern]:
        """Create message queue patterns."""
        patterns: list[RemoteCallPattern] = []

        # RabbitMQ @RabbitListener with literal queue (no ${...})
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.MQ_RABBITMQ,
                regex=re.compile(
                    r"@RabbitListener\s*\(\s*queues\s*=\s*\"([^\$][^\"]+)\"\s*[^)]*\)",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.LITERAL.value,
                extractor=self._extract_rabbit_listener_literal,
            )
        )

        # RabbitMQ @RabbitListener with variable reference ${...}
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.MQ_RABBITMQ,
                regex=re.compile(
                    r"@RabbitListener\s*\(\s*queues\s*=\s*\"\$\{([^\}]+)\}\"\s*[^)]*\)",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.VARIABLE.value,
                extractor=self._extract_rabbit_listener_variable,
            )
        )

        # Kafka @KafkaListener with literal topic (no ${...})
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.MQ_KAFKA,
                regex=re.compile(
                    r"@KafkaListener\s*\(\s*topics\s*=\s*\"([^\$][^\"]+)\"\s*[^)]*\)",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.LITERAL.value,
                extractor=self._extract_kafka_listener_literal,
            )
        )

        # Kafka @KafkaListener with variable reference ${...}
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.MQ_KAFKA,
                regex=re.compile(
                    r"@KafkaListener\s*\(\s*topics\s*=\s*\"\$\{([^\}]+)\}\"\s*[^)]*\)",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.VARIABLE.value,
                extractor=self._extract_kafka_listener_variable,
            )
        )

        # RocketMQ @RocketMQMessageListener
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.MQ_ROCKETMQ,
                regex=re.compile(
                    r"@RocketMQMessageListener\s*\(\s*"
                    r"topic\s*=\s*\"([^\"]+)\""
                    r"(?:\s*,\s*consumerGroup\s*=\s*\"([^\"]+)\"\s*)?"
                    r"[^)]*\)",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.LITERAL.value,
                extractor=self._extract_rocketmq_listener,
            )
        )

        return patterns

    def _create_grpc_patterns(self) -> list[RemoteCallPattern]:
        """Create gRPC patterns."""
        patterns: list[RemoteCallPattern] = []

        # gRPC service stub declaration
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.GRPC,
                regex=re.compile(
                    r"(\w+)Grpc\s*\.\s*\w+Stub",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.ANNOTATION.value,
                extractor=self._extract_grpc_stub,
            )
        )

        # gRPC newBlockingStub/newStub
        patterns.append(
            RemoteCallPattern(
                call_type=RemoteCallType.GRPC,
                regex=re.compile(
                    r"(\w+)Grpc\s*\.\s*new(?:Blocking)?Stub",
                    re.MULTILINE,
                ),
                confidence_base=ConfidenceLevel.LITERAL.value,
                extractor=self._extract_grpc_new_stub,
            )
        )

        return patterns

    # Extractor methods for Dubbo
    def _extract_dubbo_reference_params(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract Dubbo reference with parameters."""
        interface = match.group(1) if match.group(1) else None
        version = match.group(2) if match.lastindex and match.lastindex >= 2 else None
        group = match.group(3) if match.lastindex and match.lastindex >= 3 else None
        return {
            "interface": interface,
            "version": version,
            "group": group,
        }

    def _extract_dubbo_reference_simple(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract simple Dubbo reference."""
        # Group 1 is the type (UserService), group 2 is the variable name (userService)
        interface = match.group(1) if match.group(1) else None
        return {
            "interface": interface,
        }

    def _extract_dubbo_service(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract Dubbo service annotation."""
        version = match.group(1) if match.group(1) else None
        group = match.group(2) if match.lastindex and match.lastindex >= 2 else None
        return {
            "version": version,
            "group": group,
        }

    # Extractor methods for Feign
    def _extract_feign_client(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract Feign client annotation."""
        service_name = match.group(1)
        url = match.group(2) if match.lastindex and match.lastindex >= 2 else None
        return {
            "service_name": service_name,
            "url": url,
        }

    # Extractor methods for HTTP
    def _extract_rest_template(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract RestTemplate call."""
        method = match.group(1).upper()
        url = match.group(2)
        return {
            "method": method,
            "url": url,
        }

    def _extract_rest_template_variable(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract RestTemplate call with variable URL."""
        method = match.group(1).upper()
        return {
            "method": method,
            "url_variable": match.group(2),
        }

    def _extract_web_client(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract WebClient call."""
        method = match.group(1).upper()
        return {
            "method": method,
        }

    def _extract_okhttp(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract OkHttpClient usage."""
        return {}

    # Extractor methods for MQ
    def _extract_rabbit_listener_literal(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract RabbitListener with literal queue."""
        queue = match.group(1)
        return {
            "url": queue,
        }

    def _extract_rabbit_listener_variable(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract RabbitListener with variable queue."""
        return {
            "url_variable": match.group(1),
        }

    def _extract_kafka_listener_literal(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract KafkaListener with literal topic."""
        topic = match.group(1)
        return {
            "url": topic,
        }

    def _extract_kafka_listener_variable(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract KafkaListener with variable topic."""
        return {
            "url_variable": match.group(1),
        }

    def _extract_rocketmq_listener(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract RocketMQ listener annotation."""
        topic = match.group(1)
        group = match.group(2) if match.lastindex and match.lastindex >= 2 else None
        return {
            "url": topic,
            "group": group,
        }

    # Extractor methods for gRPC
    def _extract_grpc_stub(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract gRPC service stub."""
        service = match.group(1)
        return {
            "service_name": service,
        }

    def _extract_grpc_new_stub(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract gRPC new stub creation."""
        service = match.group(1)
        return {
            "service_name": service,
        }

    def find_patterns(self, content: str, file_path: str) -> list[RemoteCallInfo]:
        """Find all remote call patterns in source code.

        Args:
            content: Java source code content
            file_path: Path to the source file

        Returns:
            List of detected remote call information
        """
        results: list[RemoteCallInfo] = []
        seen_positions: set[int] = set()

        for pattern in self._patterns:
            for match in pattern.regex.finditer(content):
                # Avoid duplicate matches at same position
                if match.start() in seen_positions:
                    continue
                seen_positions.add(match.start())

                # Extract endpoint info
                extracted = pattern.extractor(match)

                # Calculate line number
                line_num = content[: match.start()].count("\n") + 1

                # Build endpoint
                endpoint = RemoteEndpoint(
                    service_name=extracted.get("service_name"),
                    interface=extracted.get("interface"),
                    method=extracted.get("method"),
                    url=extracted.get("url"),
                    version=extracted.get("version"),
                    group=extracted.get("group"),
                )

                # Build metadata
                metadata: dict[str, Any] = {}
                if extracted.get("url_variable"):
                    metadata["url_variable"] = extracted["url_variable"]
                if extracted.get("method"):
                    metadata["http_method"] = extracted["method"]

                call_info = RemoteCallInfo(
                    call_type=pattern.call_type,
                    endpoint=endpoint,
                    caller_class=self._extract_class_name(file_path),
                    confidence=pattern.confidence_base,
                    source_line=line_num,
                    source_file=file_path,
                    annotation=match.group(0).split("\n")[0].strip()[:100],
                    metadata=metadata,
                )
                results.append(call_info)

        logger.debug(f"Found {len(results)} remote call patterns in {file_path}")
        return results

    def _extract_class_name(self, file_path: str) -> str:
        """Extract class name from file path.

        Args:
            file_path: Path to Java source file

        Returns:
            Class name (file name without .java extension)
        """
        path = Path(file_path)
        class_name = path.stem  # filename without extension
        return class_name

    def analyze_file(self, file_path: Path) -> list[RemoteCallInfo]:
        """Analyze a Java file for remote call patterns.

        Args:
            file_path: Path to the Java file

        Returns:
            List of detected remote calls
        """
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return []

        return self.find_patterns(content, str(file_path))