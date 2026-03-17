"""Reflection call information models for Java reflection analysis.

This module provides data models for representing Java reflection calls
detected in source code, including their inferred targets and confidence levels.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReflectionType(Enum):
    """Types of Java reflection calls.

    Attributes:
        FOR_NAME: Class.forName() dynamic class loading
        GET_METHOD: getMethod() or getDeclaredMethod() method retrieval
        INVOKE: Method.invoke() method invocation
        PROXY: Proxy.newProxyInstance() dynamic proxy
        CONSTRUCTOR: getConstructor() or newInstance() constructor calls
        FIELD: getField(), get(), set() field operations
    """

    FOR_NAME = "for_name"
    GET_METHOD = "get_method"
    INVOKE = "invoke"
    PROXY = "proxy"
    CONSTRUCTOR = "constructor"
    FIELD = "field"


class InferenceSource(Enum):
    """Source of inference for reflection target.

    Attributes:
        LITERAL: Direct string literal (high confidence)
        VARIABLE: Variable reference (medium confidence)
        CONFIG: From configuration file (medium confidence)
        DYNAMIC: Runtime determined (low confidence)
        CHAINED: Part of a call chain (contextual confidence)
    """

    LITERAL = "literal"
    VARIABLE = "variable"
    CONFIG = "config"
    DYNAMIC = "dynamic"
    CHAINED = "chained"


@dataclass
class ReflectionCallInfo:
    """Information about a detected reflection call.

    Attributes:
        call_type: Type of reflection call
        target_class: Inferred target class name (may be None)
        target_method: Inferred target method name (may be None)
        confidence: Confidence level 0.0-1.0
        source_line: Line number in source file
        source_file: Path to source file
        inference_source: How the target was inferred
        raw_expression: The original reflection expression
        context: Additional context information
    """

    call_type: ReflectionType
    target_class: str | None
    target_method: str | None
    confidence: float
    source_line: int
    source_file: str
    inference_source: InferenceSource
    raw_expression: str
    context: dict[str, Any] = field(default_factory=dict)

    def is_high_confidence(self) -> bool:
        """Check if this call has high confidence.

        Returns:
            True if confidence >= 0.8
        """
        return self.confidence >= 0.8

    def full_target(self) -> str | None:
        """Get full target identifier.

        Returns:
            "ClassName.methodName" if both are set, None otherwise
        """
        if self.target_class and self.target_method:
            return f"{self.target_class}.{self.target_method}"
        return None


@dataclass
class ReflectionChain:
    """A chain of related reflection calls.

    Represents a sequence of reflection operations that together
    perform a complete action (e.g., Class.forName().getMethod().invoke()).

    Attributes:
        calls: List of reflection calls in sequence
        inferred_target: Final inferred target of the chain
        overall_confidence: Combined confidence of the chain
    """

    calls: list[ReflectionCallInfo]
    inferred_target: str | None
    overall_confidence: float

    def is_complete(self) -> bool:
        """Check if the chain has a complete target.

        Returns:
            True if both class and method are known
        """
        return self.inferred_target is not None

    def get_chain_summary(self) -> str:
        """Get a summary of the reflection chain.

        Returns:
            String representation of the chain
        """
        operations = [call.call_type.value for call in self.calls]
        return " -> ".join(operations)
