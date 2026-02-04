"""TestGeneratorService 单元测试."""

from pathlib import Path
from unittest.mock import MagicMock

from jcia.core.entities.test_case import TestCase, TestPriority


class TestTestGeneratorService:
    """TestGeneratorService测试类."""

    def test_generate_tests_for_classes(self) -> None:
        """测试为指定类生成测试."""
        from jcia.core.interfaces.ai_service import TestGenerationRequest
        from jcia.core.services.test_generator_service import TestGeneratorService

        ai_generator = MagicMock()
        service = TestGeneratorService(ai_generator)

        # Mock AI response
        mock_test = TestCase(
            class_name="UserServiceTest",
            method_name="testCreateUser",
            target_class="UserService",
            target_method="createUser",
        )
        response_mock = MagicMock()
        response_mock.test_cases = [mock_test]
        response_mock.confidence = 0.8
        ai_generator.generate_tests.return_value = response_mock

        # Act
        request = TestGenerationRequest(
            target_classes=["UserService"],
            code_snippets={"UserService": "public class UserService {...}"},
            context={},
        )
        result = service.generate_tests(request, Path("/test/project"))

        # Assert
        assert len(result.test_cases) == 1
        assert result.test_cases[0].target_class == "UserService"

    def test_generate_for_uncovered_code(self) -> None:
        """测试为未覆盖代码生成测试."""
        from jcia.core.services.test_generator_service import TestGeneratorService

        ai_generator = MagicMock()
        service = TestGeneratorService(ai_generator)

        # Mock AI response
        response_mock = MagicMock()
        response_mock.test_cases = []
        response_mock.confidence = 0.7
        ai_generator.generate_for_uncovered.return_value = response_mock

        # Act
        coverage_data = {
            "uncovered_classes": ["PaymentService"],
            "uncovered_methods": ["PaymentService.processPayment"],
        }
        _ = service.generate_for_uncovered(coverage_data, Path("/test/project"))

        # Assert
        ai_generator.generate_for_uncovered.assert_called_once()

    def test_refine_test_case(self) -> None:
        """测试优化测试用例."""
        from jcia.core.services.test_generator_service import TestGeneratorService

        ai_generator = MagicMock()
        service = TestGeneratorService(ai_generator)

        original_test = TestCase(
            class_name="UserServiceTest",
            method_name="testCreateUser",
            target_class="UserService",
        )

        # Mock AI response
        refined_test = TestCase(
            class_name="UserServiceTest",
            method_name="testCreateUserWithValidation",
            target_class="UserService",
        )
        ai_generator.refine_test.return_value = refined_test

        # Act
        feedback = "Add validation test for empty username"
        result = service.refine_test_case(original_test, feedback, Path("/test/project"))

        # Assert
        assert result.method_name == "testCreateUserWithValidation"

    def test_merge_generated_tests(self) -> None:
        """测试合并生成的测试用例."""
        from jcia.core.services.test_generator_service import TestGeneratorService

        ai_generator = MagicMock()
        service = TestGeneratorService(ai_generator)

        test1 = TestCase(
            class_name="Service1Test",
            method_name="testMethod1",
            target_class="Service1",
        )
        test2 = TestCase(
            class_name="Service2Test",
            method_name="testMethod2",
            target_class="Service2",
        )
        test3 = TestCase(
            class_name="Service1Test",
            method_name="testMethod1",  # Duplicate
            target_class="Service1",
        )

        # Act
        result = service.merge_test_cases([[test1], [test2, test3]])

        # Assert
        assert len(result) == 2  # Duplicate should be removed

    def test_prioritize_generated_tests(self) -> None:
        """测试对生成的测试用例排序."""
        from jcia.core.services.test_generator_service import TestGeneratorService

        ai_generator = MagicMock()
        service = TestGeneratorService(ai_generator)

        test_critical = TestCase(
            class_name="AuthServiceTest",
            method_name="testLogin",
            target_class="AuthService",
            priority=TestPriority.CRITICAL,
        )
        test_low = TestCase(
            class_name="UtilServiceTest",
            method_name="testFormat",
            target_class="UtilService",
            priority=TestPriority.LOW,
        )

        # Act
        result = service.prioritize_tests([test_low, test_critical])

        # Assert
        assert result[0].priority == TestPriority.CRITICAL
        assert result[1].priority == TestPriority.LOW

    def test_filter_by_confidence(self) -> None:
        """测试按置信度过滤测试."""
        from jcia.core.interfaces.ai_service import TestGenerationResponse
        from jcia.core.services.test_generator_service import TestGeneratorService

        ai_generator = MagicMock()
        service = TestGeneratorService(ai_generator)

        # Create response with low confidence
        response = TestGenerationResponse(
            test_cases=[],
            explanations=["Low quality test"],
            confidence=0.3,
            tokens_used=100,
        )

        # Act
        filtered = service.filter_by_confidence(response, min_confidence=0.5)

        # Assert
        assert filtered.test_cases == []

    def test_analyze_code_for_testability(self) -> None:
        """测试分析代码的可测试性."""
        from jcia.core.services.test_generator_service import TestGeneratorService

        ai_generator = MagicMock()
        service = TestGeneratorService(ai_generator)

        code = """
        public class Calculator {
            public int add(int a, int b) {
                return a + b;
            }
        }
        """

        # Act
        result = service.analyze_testability(code)

        # Assert
        assert "testable_methods" in result
        assert "suggestions" in result
