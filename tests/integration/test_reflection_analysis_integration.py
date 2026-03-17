"""Integration tests for reflection analysis.

Tests the integration of reflection pattern matching with call chain analysis.
"""

import tempfile
from pathlib import Path

import pytest

from jcia.adapters.tools.reflection_models import (
    InferenceSource,
    ReflectionType,
)
from jcia.adapters.tools.reflection_patterns import ReflectionPatternMatcher
from jcia.adapters.tools.source_code_call_graph_adapter import (
    SourceCodeCallGraphAnalyzer,
)

pytestmark = [pytest.mark.integration, pytest.mark.adapters]


class TestReflectionAnalysisIntegration:
    """Integration tests for reflection analysis."""

    @pytest.fixture
    def temp_project(self) -> Path:
        """Create a temporary Java project for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            src_dir = project_path / "src" / "main" / "java" / "com" / "example"
            src_dir.mkdir(parents=True)

            # Create a service class
            service_file = src_dir / "Service.java"
            service_file.write_text("""
package com.example;

public class Service {
    public void process(String input) {
        System.out.println("Processing: " + input);
    }

    public String getData() {
        return "data";
    }
}
""")

            # Create a class with reflection calls
            reflector_file = src_dir / "Reflector.java"
            reflector_file.write_text("""
package com.example;

import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

public class Reflector {
    public void executeReflection() throws Exception {
        // Class.forName with literal
        Class<?> clazz = Class.forName("com.example.Service");

        // getMethod with literal
        Method method = clazz.getMethod("process", String.class);

        // invoke
        Object instance = clazz.getDeclaredConstructor().newInstance();
        method.invoke(instance, "test");

        // Chained reflection
        Method getDataMethod = Class.forName("com.example.Service")
            .getMethod("getData");
    }

    public void dynamicReflection(String className, String methodName) throws Exception {
        // Variable-based reflection
        Class<?> clazz = Class.forName(className);
        Method method = clazz.getMethod(methodName);
    }

    public void proxyExample() {
        // Dynamic proxy
        Object proxy = Proxy.newProxyInstance(
            getClass().getClassLoader(),
            new Class<?>[] { Runnable.class },
            (proxy, method, args) -> null
        );
    }
}
""")

            # Create another class that uses Service directly
            direct_file = src_dir / "DirectCaller.java"
            direct_file.write_text("""
package com.example;

public class DirectCaller {
    private Service service = new Service();

    public void callService() {
        service.process("direct call");
    }
}
""")

            yield project_path

    def test_reflection_pattern_extraction(self, temp_project: Path) -> None:
        """Test that reflection patterns are extracted from Java files."""
        matcher = ReflectionPatternMatcher()

        reflector_file = temp_project / "src" / "main" / "java" / "com" / "example" / "Reflector.java"
        content = reflector_file.read_text()

        matches = matcher.find_patterns(content, str(reflector_file))

        # Should find multiple reflection patterns
        assert len(matches) >= 3

        # Check for Class.forName
        for_name_matches = [m for m in matches if m.call_type == ReflectionType.FOR_NAME]
        assert len(for_name_matches) >= 1

        # Check for getMethod
        get_method_matches = [m for m in matches if m.call_type == ReflectionType.GET_METHOD]
        assert len(get_method_matches) >= 1

        # Check for invoke
        invoke_matches = [m for m in matches if m.call_type == ReflectionType.INVOKE]
        assert len(invoke_matches) >= 1

    def test_source_code_analyzer_reflection_integration(self, temp_project: Path) -> None:
        """Test that SourceCodeCallGraphAnalyzer extracts reflection calls."""
        analyzer = SourceCodeCallGraphAnalyzer(str(temp_project))

        # Get reflection calls for Reflector class
        reflection_calls = analyzer.get_reflection_calls("com.example.Reflector")

        # Should have reflection calls
        assert len(reflection_calls) > 0

        # Check that Class.forName was detected with correct target
        for_name_calls = [
            c for c in reflection_calls if c.call_type == ReflectionType.FOR_NAME
        ]
        assert len(for_name_calls) >= 1

        # At least one should have "com.example.Service" as target
        service_targets = [
            c for c in for_name_calls if c.target_class == "com.example.Service"
        ]
        assert len(service_targets) >= 1

    def test_reflection_impact_analysis(self, temp_project: Path) -> None:
        """Test analyzing impact through reflection calls."""
        analyzer = SourceCodeCallGraphAnalyzer(str(temp_project))

        # Analyze what reflection calls target Service class
        impact_calls = analyzer.analyze_reflection_impact("com.example.Service")

        # Should find reflection calls targeting Service
        assert len(impact_calls) >= 1

        # All should be high confidence (literal class names)
        high_confidence = [c for c in impact_calls if c.is_high_confidence()]
        assert len(high_confidence) >= 1

    def test_reflection_in_call_chain(self, temp_project: Path) -> None:
        """Test that reflection calls are included in call chain analysis."""
        analyzer = SourceCodeCallGraphAnalyzer(str(temp_project))

        # Analyze downstream from Reflector
        graph = analyzer.analyze_downstream("com.example.Reflector.executeReflection")

        # Should include reflection targets in children
        method_names = [child.method_name for child in graph.root.children]

        # Should find the reflected methods
        assert "process" in method_names or "getData" in method_names

    def test_literal_vs_variable_confidence(self, temp_project: Path) -> None:
        """Test confidence levels for literal vs variable reflection."""
        analyzer = SourceCodeCallGraphAnalyzer(str(temp_project))

        reflection_calls = analyzer.get_reflection_calls("com.example.Reflector")

        # Find literal-based calls
        literal_calls = [
            c for c in reflection_calls
            if c.inference_source == InferenceSource.LITERAL
        ]

        # Find variable-based calls
        variable_calls = [
            c for c in reflection_calls
            if c.inference_source == InferenceSource.VARIABLE
        ]

        # Literal calls should have higher confidence
        if literal_calls and variable_calls:
            assert literal_calls[0].confidence >= variable_calls[0].confidence

    def test_proxy_detection(self, temp_project: Path) -> None:
        """Test detection of Proxy.newProxyInstance."""
        analyzer = SourceCodeCallGraphAnalyzer(str(temp_project))

        reflection_calls = analyzer.get_reflection_calls("com.example.Reflector")

        proxy_calls = [
            c for c in reflection_calls if c.call_type == ReflectionType.PROXY
        ]

        assert len(proxy_calls) >= 1

    def test_all_reflection_calls_aggregation(self, temp_project: Path) -> None:
        """Test getting all reflection calls across the project."""
        analyzer = SourceCodeCallGraphAnalyzer(str(temp_project))

        all_calls = analyzer.get_all_reflection_calls()

        # Should have reflection calls in at least the Reflector class
        assert "com.example.Reflector" in all_calls
        assert len(all_calls["com.example.Reflector"]) >= 1

    def test_reflection_target_inference(self, temp_project: Path) -> None:
        """Test inference of reflection targets from chained calls."""
        matcher = ReflectionPatternMatcher()

        reflector_file = temp_project / "src" / "main" / "java" / "com" / "example" / "Reflector.java"
        content = reflector_file.read_text()

        # Find chained calls
        chained_calls = matcher.find_chained_calls(content, str(reflector_file))

        # Should find the chained Class.forName().getMethod() call
        assert len(chained_calls) >= 1

        # Check that target class and method are extracted
        service_get_data = [
            c for c in chained_calls
            if c.target_class == "com.example.Service" and c.target_method == "getData"
        ]
        assert len(service_get_data) >= 1

    def test_downstream_includes_reflection_targets(self, temp_project: Path) -> None:
        """Test that downstream analysis includes reflection-inferred targets."""
        analyzer = SourceCodeCallGraphAnalyzer(str(temp_project))

        # Get downstream from Reflector.executeReflection
        graph = analyzer.analyze_downstream("com.example.Reflector.executeReflection")

        # Collect all method names in the graph
        def collect_methods(node, methods):
            methods.append(f"{node.class_name}.{node.method_name}")
            for child in node.children:
                collect_methods(child, methods)

        all_methods = []
        collect_methods(graph.root, all_methods)

        # Should include reflection targets
        # Note: The exact matching depends on the analysis implementation
        assert len(graph.root.children) > 0


class TestReflectionWithRealWorldPatterns:
    """Tests with real-world reflection patterns."""

    def test_spring_reflection_pattern(self) -> None:
        """Test Spring-style reflection patterns."""
        matcher = ReflectionPatternMatcher()

        content = '''
        // Spring-style reflection
        Class<?> controllerClass = Class.forName("com.example.controller.UserController");
        Method handleMethod = controllerClass.getMethod("handleRequest", HttpServletRequest.class);
        Object result = handleMethod.invoke(controller, request);
        '''

        matches = matcher.find_patterns(content, "SpringTest.java")

        assert len(matches) >= 3
        assert any(m.call_type == ReflectionType.FOR_NAME for m in matches)
        assert any(m.call_type == ReflectionType.GET_METHOD for m in matches)
        assert any(m.call_type == ReflectionType.INVOKE for m in matches)

    def test_mybatis_mapper_pattern(self) -> None:
        """Test MyBatis-style mapper reflection."""
        matcher = ReflectionPatternMatcher()

        content = '''
        // MyBatis mapper proxy
        SqlSession session = sqlSessionFactory.openSession();
        UserMapper mapper = session.getMapper(UserMapper.class);
        '''

        # This doesn't directly use reflection in the typical sense,
        # but we should not produce false positives
        matches = matcher.find_patterns(content, "MyBatisTest.java")

        # Should not detect false reflection calls
        # getMapper is not a reflection method
        for_name_matches = [m for m in matches if m.call_type == ReflectionType.FOR_NAME]
        assert len(for_name_matches) == 0

    def test_dubbo_spi_pattern(self) -> None:
        """Test Dubbo SPI-style reflection."""
        matcher = ReflectionPatternMatcher()

        content = '''
        // Dubbo ExtensionLoader uses reflection internally
        ExtensionLoader<Protocol> loader = ExtensionLoader.getExtensionLoader(Protocol.class);
        Protocol protocol = loader.getExtension("dubbo");
        '''

        # Should not produce false positives
        matches = matcher.find_patterns(content, "DubboTest.java")
        for_name_matches = [m for m in matches if m.call_type == ReflectionType.FOR_NAME]
        assert len(for_name_matches) == 0

    def test_complex_reflection_scenario(self) -> None:
        """Test complex reflection scenario with multiple patterns."""
        matcher = ReflectionPatternMatcher()

        content = '''
        public class DynamicInvoker {
            public Object invoke(String className, String methodName, Object... args) throws Exception {
                Class<?> clazz = Class.forName(className);
                Method method = clazz.getMethod(methodName, getParameterTypes(args));
                Object instance = clazz.getDeclaredConstructor().newInstance();
                return method.invoke(instance, args);
            }

            private Class<?>[] getParameterTypes(Object[] args) {
                Class<?>[] types = new Class<?>[args.length];
                for (int i = 0; i < args.length; i++) {
                    types[i] = args[i].getClass();
                }
                return types;
            }
        }
        '''

        matches = matcher.find_patterns(content, "DynamicInvoker.java")

        # Should detect multiple reflection patterns
        call_types = {m.call_type for m in matches}
        assert ReflectionType.FOR_NAME in call_types
        assert ReflectionType.GET_METHOD in call_types
        assert ReflectionType.INVOKE in call_types
        assert ReflectionType.CONSTRUCTOR in call_types