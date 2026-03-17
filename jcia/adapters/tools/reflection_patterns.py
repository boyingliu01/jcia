"""Reflection pattern matcher for Java source code.

This module provides pattern matching capabilities for detecting Java reflection
calls in source code, including Class.forName, getMethod, invoke, and more.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from jcia.adapters.tools.reflection_models import (
    InferenceSource,
    ReflectionCallInfo,
    ReflectionType,
)

logger = logging.getLogger(__name__)


@dataclass
class ReflectionPattern:
    """A reflection pattern definition.

    Attributes:
        pattern_type: Type of reflection pattern
        regex: Compiled regex pattern
        extractor: Function to extract target info from match
        confidence_base: Base confidence for this pattern type
    """

    pattern_type: ReflectionType
    regex: re.Pattern[str]
    extractor: Callable[[re.Match[str]], dict[str, Any]]
    confidence_base: float


class ReflectionPatternMatcher:
    """Matcher for Java reflection patterns in source code.

    Detects various reflection patterns including:
    - Class.forName("className")
    - getMethod("methodName")
    - Method.invoke(obj, args)
    - Proxy.newProxyInstance(...)
    - Constructor.newInstance(...)
    - Field.get/set(...)

    Example:
        ```python
        matcher = ReflectionPatternMatcher()
        content = 'Class.forName("com.example.MyClass")'
        matches = matcher.find_patterns(content, "Test.java")
        for match in matches:
            print(f"Found {match.call_type}: {match.target_class}")
        ```
    """

    # Confidence levels for different inference sources
    LITERAL_CONFIDENCE = 0.95
    VARIABLE_CONFIDENCE = 0.6
    DYNAMIC_CONFIDENCE = 0.3

    def __init__(self) -> None:
        """Initialize the pattern matcher with all reflection patterns."""
        self._patterns = self._create_patterns()

    def _create_patterns(self) -> list[ReflectionPattern]:
        """Create all reflection patterns.

        Returns:
            List of compiled reflection patterns
        """
        patterns = []

        # Class.forName("className") pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.FOR_NAME,
                regex=re.compile(
                    r'Class\.forName\s*\(\s*"([^"]+)"\s*\)',
                    re.MULTILINE,
                ),
                extractor=self._extract_for_name_literal,
                confidence_base=self.LITERAL_CONFIDENCE,
            )
        )

        # Class.forName(variable) pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.FOR_NAME,
                regex=re.compile(
                    r'Class\.forName\s*\(\s*(\w+)\s*\)',
                    re.MULTILINE,
                ),
                extractor=self._extract_for_name_variable,
                confidence_base=self.VARIABLE_CONFIDENCE,
            )
        )

        # getMethod("methodName") pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.GET_METHOD,
                regex=re.compile(
                    r'\.get(?:Declared)?Method\s*\(\s*"([^"]+)"',
                    re.MULTILINE,
                ),
                extractor=self._extract_get_method_literal,
                confidence_base=self.LITERAL_CONFIDENCE,
            )
        )

        # getMethod(variable) pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.GET_METHOD,
                regex=re.compile(
                    r'\.get(?:Declared)?Method\s*\(\s*(\w+)',
                    re.MULTILINE,
                ),
                extractor=self._extract_get_method_variable,
                confidence_base=self.VARIABLE_CONFIDENCE,
            )
        )

        # Method.invoke(obj, args) pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.INVOKE,
                regex=re.compile(
                    r'\.invoke\s*\(\s*(\w+)\s*(?:,\s*(.+?))?\s*\)',
                    re.MULTILINE,
                ),
                extractor=self._extract_invoke,
                confidence_base=self.VARIABLE_CONFIDENCE,
            )
        )

        # Proxy.newProxyInstance pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.PROXY,
                regex=re.compile(
                    r'Proxy\.newProxyInstance\s*\(',
                    re.MULTILINE,
                ),
                extractor=self._extract_proxy,
                confidence_base=self.DYNAMIC_CONFIDENCE,
            )
        )

        # getConstructor pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.CONSTRUCTOR,
                regex=re.compile(
                    r'\.get(?:Declared)?Constructor\s*\(',
                    re.MULTILINE,
                ),
                extractor=self._extract_constructor,
                confidence_base=self.DYNAMIC_CONFIDENCE,
            )
        )

        # newInstance pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.CONSTRUCTOR,
                regex=re.compile(
                    r'\.newInstance\s*\(',
                    re.MULTILINE,
                ),
                extractor=self._extract_new_instance,
                confidence_base=self.DYNAMIC_CONFIDENCE,
            )
        )

        # getField/getDeclaredField pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.FIELD,
                regex=re.compile(
                    r'\.get(?:Declared)?Field\s*\(\s*"([^"]+)"\s*\)',
                    re.MULTILINE,
                ),
                extractor=self._extract_field_literal,
                confidence_base=self.LITERAL_CONFIDENCE,
            )
        )

        # Field.get pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.FIELD,
                regex=re.compile(
                    r'\.get\s*\(\s*(\w+)\s*\)',
                    re.MULTILINE,
                ),
                extractor=self._extract_field_get,
                confidence_base=self.VARIABLE_CONFIDENCE,
            )
        )

        # Field.set pattern
        patterns.append(
            ReflectionPattern(
                pattern_type=ReflectionType.FIELD,
                regex=re.compile(
                    r'\.set\s*\(\s*(\w+)\s*,',
                    re.MULTILINE,
                ),
                extractor=self._extract_field_set,
                confidence_base=self.VARIABLE_CONFIDENCE,
            )
        )

        return patterns

    def find_patterns(self, content: str, file_path: str) -> list[ReflectionCallInfo]:
        """Find all reflection patterns in source code.

        Args:
            content: Java source code content
            file_path: Path to the source file

        Returns:
            List of detected reflection call information
        """
        results: list[ReflectionCallInfo] = []
        seen_positions: set[int] = set()

        for pattern in self._patterns:
            for match in pattern.regex.finditer(content):
                # Avoid duplicate matches at same position
                if match.start() in seen_positions:
                    continue
                seen_positions.add(match.start())

                # Extract target info
                extracted = pattern.extractor(match)

                # Calculate line number
                line_num = content[: match.start()].count("\n") + 1

                # Determine inference source
                inference_source = self._determine_inference_source(
                    extracted, pattern.confidence_base
                )

                call_info = ReflectionCallInfo(
                    call_type=pattern.pattern_type,
                    target_class=extracted.get("target_class"),
                    target_method=extracted.get("target_method"),
                    confidence=pattern.confidence_base,
                    source_line=line_num,
                    source_file=file_path,
                    inference_source=inference_source,
                    raw_expression=match.group(0),
                    context=extracted.get("context", {}),
                )
                results.append(call_info)

        logger.debug(f"Found {len(results)} reflection patterns in {file_path}")
        return results

    def find_chained_calls(self, content: str, file_path: str) -> list[ReflectionCallInfo]:
        """Find chained reflection calls like Class.forName().getMethod().invoke().

        Args:
            content: Java source code content
            file_path: Path to the source file

        Returns:
            List of reflection call information from chains
        """
        results: list[ReflectionCallInfo] = []

        # Pattern for chained reflection calls
        chain_pattern = re.compile(
            r'Class\.forName\s*\(\s*"([^"]+)"\s*\)'
            r'(?:\s*\.\s*get(?:Declared)?Method\s*\(\s*"([^"]+)"\s*[^)]*\))?'
            r'(?:\s*\.\s*invoke\s*\([^)]+\))?',
            re.MULTILINE,
        )

        for match in chain_pattern.finditer(content):
            target_class = match.group(1)
            target_method = match.group(2)  # May be None

            line_num = content[: match.start()].count("\n") + 1

            # Build the complete chain
            confidence = self.LITERAL_CONFIDENCE
            if target_method:
                # Complete chain with class and method
                confidence = self.LITERAL_CONFIDENCE * 0.95  # Slight reduction for chain

            call_info = ReflectionCallInfo(
                call_type=ReflectionType.FOR_NAME,
                target_class=target_class,
                target_method=target_method,
                confidence=confidence,
                source_line=line_num,
                source_file=file_path,
                inference_source=InferenceSource.CHAINED,
                raw_expression=match.group(0),
                context={"is_chain": True},
            )
            results.append(call_info)

        return results

    # Extractor methods
    def _extract_for_name_literal(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract class name from Class.forName("literal")."""
        return {
            "target_class": match.group(1),
            "inference": InferenceSource.LITERAL,
        }

    def _extract_for_name_variable(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract variable name from Class.forName(variable)."""
        return {
            "target_class": None,
            "context": {"variable": match.group(1)},
        }

    def _extract_get_method_literal(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract method name from getMethod("literal")."""
        return {
            "target_method": match.group(1),
        }

    def _extract_get_method_variable(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract variable name from getMethod(variable)."""
        return {
            "target_method": None,
            "context": {"variable": match.group(1)},
        }

    def _extract_invoke(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract info from Method.invoke(obj, args)."""
        return {
            "context": {
                "target_object": match.group(1),
                "args": match.group(2) if match.lastindex >= 2 else None,
            },
        }

    def _extract_proxy(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract info from Proxy.newProxyInstance()."""
        return {
            "context": {"is_dynamic_proxy": True},
        }

    def _extract_constructor(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract info from getConstructor()."""
        return {
            "context": {"is_constructor": True},
        }

    def _extract_new_instance(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract info from newInstance()."""
        return {
            "context": {"is_new_instance": True},
        }

    def _extract_field_literal(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract field name from getField("literal")."""
        return {
            "target_method": match.group(1),  # Field name stored as method
            "context": {"is_field": True},
        }

    def _extract_field_get(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract info from Field.get(obj)."""
        return {
            "context": {
                "operation": "get",
                "target_object": match.group(1),
            },
        }

    def _extract_field_set(self, match: re.Match[str]) -> dict[str, Any]:
        """Extract info from Field.set(obj, value)."""
        return {
            "context": {
                "operation": "set",
                "target_object": match.group(1),
            },
        }

    def _determine_inference_source(
        self, extracted: dict[str, Any], confidence_base: float
    ) -> InferenceSource:
        """Determine the inference source based on extracted info.

        Args:
            extracted: Extracted information from pattern
            confidence_base: Base confidence level

        Returns:
            InferenceSource enum value
        """
        # If we have a literal target, it's literal inference
        if extracted.get("target_class") or extracted.get("target_method"):
            if confidence_base >= self.LITERAL_CONFIDENCE:
                return InferenceSource.LITERAL
            return InferenceSource.VARIABLE

        # Check for variable context
        if extracted.get("context", {}).get("variable"):
            return InferenceSource.VARIABLE

        # Default to dynamic
        return InferenceSource.DYNAMIC

    def analyze_file(self, file_path: Path) -> list[ReflectionCallInfo]:
        """Analyze a Java file for reflection patterns.

        Args:
            file_path: Path to the Java file

        Returns:
            List of detected reflection calls
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