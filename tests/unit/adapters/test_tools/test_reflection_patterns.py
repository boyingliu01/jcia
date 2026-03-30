"""Unit tests for reflection pattern matching.

Tests for detecting Java reflection patterns in source code.
"""

import pytest

from jcia.adapters.tools.reflection_models import (
    InferenceSource,
    ReflectionType,
)
from jcia.adapters.tools.reflection_patterns import ReflectionPatternMatcher

pytestmark = [pytest.mark.unit, pytest.mark.adapters, pytest.mark.tools]


class TestReflectionPatternMatcher:
    """Tests for ReflectionPatternMatcher."""

    @pytest.fixture
    def matcher(self) -> ReflectionPatternMatcher:
        """Create a pattern matcher instance."""
        return ReflectionPatternMatcher()

    # Class.forName tests
    def test_match_class_for_name_literal(self, matcher: ReflectionPatternMatcher) -> None:
        """Test Class.forName with string literal."""
        content = 'Class.forName("com.example.MyClass")'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.FOR_NAME
        assert matches[0].target_class == "com.example.MyClass"
        assert matches[0].confidence >= 0.9
        assert matches[0].inference_source == InferenceSource.LITERAL

    def test_match_class_for_name_variable(self, matcher: ReflectionPatternMatcher) -> None:
        """Test Class.forName with variable."""
        content = 'String className = "MyClass"; Class.forName(className)'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) >= 1
        assert matches[0].call_type == ReflectionType.FOR_NAME
        assert matches[0].inference_source == InferenceSource.VARIABLE

    def test_match_class_for_name_multiline(self, matcher: ReflectionPatternMatcher) -> None:
        """Test Class.forName spanning multiple lines."""
        content = '''
        Class.forName(
            "com.example.MyClass"
        )
        '''
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].target_class == "com.example.MyClass"

    # getMethod tests
    def test_match_get_method(self, matcher: ReflectionPatternMatcher) -> None:
        """Test getMethod with string literal."""
        content = 'clazz.getMethod("process", String.class)'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.GET_METHOD
        assert matches[0].target_method == "process"

    def test_match_get_declared_method(self, matcher: ReflectionPatternMatcher) -> None:
        """Test getDeclaredMethod."""
        content = 'clazz.getDeclaredMethod("privateMethod")'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.GET_METHOD
        assert matches[0].target_method == "privateMethod"

    def test_match_get_method_variable(self, matcher: ReflectionPatternMatcher) -> None:
        """Test getMethod with variable."""
        content = 'String methodName = "process"; clazz.getMethod(methodName)'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) >= 1
        assert matches[0].call_type == ReflectionType.GET_METHOD
        assert matches[0].inference_source == InferenceSource.VARIABLE

    # invoke tests
    def test_match_invoke(self, matcher: ReflectionPatternMatcher) -> None:
        """Test Method.invoke."""
        content = 'method.invoke(obj, "arg1", "arg2")'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.INVOKE

    def test_match_invoke_no_args(self, matcher: ReflectionPatternMatcher) -> None:
        """Test Method.invoke with no arguments."""
        content = 'method.invoke(obj)'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.INVOKE

    # Proxy tests
    def test_match_proxy_new_instance(self, matcher: ReflectionPatternMatcher) -> None:
        """Test Proxy.newProxyInstance."""
        content = 'Proxy.newProxyInstance(classLoader, interfaces, handler)'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.PROXY

    # Constructor tests
    def test_match_get_constructor(self, matcher: ReflectionPatternMatcher) -> None:
        """Test getConstructor."""
        content = 'clazz.getConstructor(String.class)'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.CONSTRUCTOR

    def test_match_new_instance(self, matcher: ReflectionPatternMatcher) -> None:
        """Test Constructor.newInstance."""
        content = 'constructor.newInstance("param")'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.CONSTRUCTOR

    def test_match_get_declared_constructor(self, matcher: ReflectionPatternMatcher) -> None:
        """Test getDeclaredConstructor."""
        content = 'clazz.getDeclaredConstructor()'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.CONSTRUCTOR

    # Field tests
    def test_match_get_field(self, matcher: ReflectionPatternMatcher) -> None:
        """Test getField."""
        content = 'clazz.getField("fieldName")'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.FIELD
        assert matches[0].target_method == "fieldName"

    def test_match_get_declared_field(self, matcher: ReflectionPatternMatcher) -> None:
        """Test getDeclaredField."""
        content = 'clazz.getDeclaredField("privateField")'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.FIELD

    def test_match_field_get(self, matcher: ReflectionPatternMatcher) -> None:
        """Test Field.get."""
        content = 'field.get(obj)'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.FIELD

    def test_match_field_set(self, matcher: ReflectionPatternMatcher) -> None:
        """Test Field.set."""
        content = 'field.set(obj, value)'
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].call_type == ReflectionType.FIELD

    # Chained calls tests
    def test_chained_reflection_calls(self, matcher: ReflectionPatternMatcher) -> None:
        """Test chained reflection calls."""
        content = 'Class.forName("com.example.Service").getMethod("process").invoke(obj)'
        matches = matcher.find_patterns(content, "Test.java")
        # Should detect multiple patterns
        assert len(matches) >= 2
        # Check that we detected forName and getMethod at minimum
        call_types = {m.call_type for m in matches}
        assert ReflectionType.FOR_NAME in call_types
        assert ReflectionType.GET_METHOD in call_types

    def test_find_chained_calls(self, matcher: ReflectionPatternMatcher) -> None:
        """Test find_chained_calls method."""
        content = 'Class.forName("com.example.Service").getMethod("execute")'
        matches = matcher.find_chained_calls(content, "Test.java")
        assert len(matches) == 1
        assert matches[0].target_class == "com.example.Service"
        assert matches[0].target_method == "execute"

    # Edge cases
    def test_no_false_positives(self, matcher: ReflectionPatternMatcher) -> None:
        """Test that regular code doesn't trigger false positives."""
        content = '''
        public void process() {
            String name = "test";
            int value = 42;
            System.out.println("Hello");
            if (value > 0) {
                System.out.println("Positive");
            }
        }
        '''
        matches = matcher.find_patterns(content, "Test.java")
        # Should not detect any reflection patterns
        assert len(matches) == 0

    def test_empty_content(self, matcher: ReflectionPatternMatcher) -> None:
        """Test with empty content."""
        content = ""
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 0

    def test_multiple_patterns_in_one_file(self, matcher: ReflectionPatternMatcher) -> None:
        """Test detecting multiple reflection patterns in one file."""
        content = '''
        public class ReflectionExample {
            public void example() {
                Class<?> clazz = Class.forName("com.example.Service");
                Method method = clazz.getMethod("process");
                method.invoke(obj);
                Field field = clazz.getField("name");
            }
        }
        '''
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) >= 4
        call_types = {m.call_type for m in matches}
        assert ReflectionType.FOR_NAME in call_types
        assert ReflectionType.GET_METHOD in call_types
        assert ReflectionType.INVOKE in call_types
        assert ReflectionType.FIELD in call_types

    def test_line_number_calculation(self, matcher: ReflectionPatternMatcher) -> None:
        """Test that line numbers are calculated correctly."""
        content = '''
        public class Test {
            public void method() {
                Class.forName("com.example.Test");
            }
        }
        '''
        matches = matcher.find_patterns(content, "Test.java")
        assert len(matches) == 1
        # The Class.forName is on line 4 (0-indexed would be 3)
        assert matches[0].source_line == 4

    def test_confidence_levels(self, matcher: ReflectionPatternMatcher) -> None:
        """Test confidence levels for different patterns."""
        # Literal should have high confidence
        literal_content = 'Class.forName("com.example.Test")'
        literal_matches = matcher.find_patterns(literal_content, "Test.java")
        assert literal_matches[0].is_high_confidence()

        # Variable should have medium confidence
        variable_content = 'Class.forName(className)'
        variable_matches = matcher.find_patterns(variable_content, "Test.java")
        assert not variable_matches[0].is_high_confidence()


class TestReflectionCallInfo:
    """Tests for ReflectionCallInfo dataclass."""

    def test_is_high_confidence_true(self) -> None:
        """Test is_high_confidence returns True for confidence >= 0.8."""
        from jcia.adapters.tools.reflection_models import ReflectionCallInfo

        info = ReflectionCallInfo(
            call_type=ReflectionType.FOR_NAME,
            target_class="com.example.Test",
            target_method=None,
            confidence=0.95,
            source_line=1,
            source_file="Test.java",
            inference_source=InferenceSource.LITERAL,
            raw_expression='Class.forName("com.example.Test")',
        )
        assert info.is_high_confidence() is True

    def test_is_high_confidence_false(self) -> None:
        """Test is_high_confidence returns False for confidence < 0.8."""
        from jcia.adapters.tools.reflection_models import ReflectionCallInfo

        info = ReflectionCallInfo(
            call_type=ReflectionType.FOR_NAME,
            target_class=None,
            target_method=None,
            confidence=0.5,
            source_line=1,
            source_file="Test.java",
            inference_source=InferenceSource.VARIABLE,
            raw_expression="Class.forName(className)",
        )
        assert info.is_high_confidence() is False

    def test_full_target_with_both(self) -> None:
        """Test full_target returns combined string when both class and method are set."""
        from jcia.adapters.tools.reflection_models import ReflectionCallInfo

        info = ReflectionCallInfo(
            call_type=ReflectionType.GET_METHOD,
            target_class="com.example.Service",
            target_method="process",
            confidence=0.9,
            source_line=1,
            source_file="Test.java",
            inference_source=InferenceSource.LITERAL,
            raw_expression='clazz.getMethod("process")',
        )
        assert info.full_target() == "com.example.Service.process"

    def test_full_target_missing_method(self) -> None:
        """Test full_target returns None when method is missing."""
        from jcia.adapters.tools.reflection_models import ReflectionCallInfo

        info = ReflectionCallInfo(
            call_type=ReflectionType.FOR_NAME,
            target_class="com.example.Service",
            target_method=None,
            confidence=0.9,
            source_line=1,
            source_file="Test.java",
            inference_source=InferenceSource.LITERAL,
            raw_expression='Class.forName("com.example.Service")',
        )
        assert info.full_target() is None
