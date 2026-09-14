"""测试生成测试用例用例."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from jcia.core.entities.test_case import TestCase, TestPriority, TestType
from jcia.core.interfaces.ai_service import AIProvider
from jcia.core.use_cases.generate_tests import (
    GenerateTestsRequest,
    GenerateTestsResponse,
    GenerateTestsUseCase,
)


class TestGenerateTestsRequest:
    """测试GenerateTestsRequest."""

    def test_init_with_required_fields(self, tmp_path: Path) -> None:
        """测试使用必需字段初始化."""
        request = GenerateTestsRequest(project_path=tmp_path)
        assert request.project_path == tmp_path
        assert request.target_classes == []
        assert request.coverage_data is None
        assert request.output_dir is None
        assert request.min_confidence == 0.5
        assert request.priority == "medium"

    def test_init_with_all_fields(self, tmp_path: Path) -> None:
        """测试使用所有字段初始化."""
        request = GenerateTestsRequest(
            project_path=tmp_path,
            target_classes=["com.example.Class1", "com.example.Class2"],
            min_confidence=0.8,
            priority="high",
        )
        assert len(request.target_classes) == 2
        assert request.min_confidence == 0.8
        assert request.priority == "high"


class TestGenerateTestsResponse:
    """测试GenerateTestsResponse."""

    def test_init(self) -> None:
        """测试初始化."""
        test_case = Mock(spec=TestCase)
        response = GenerateTestsResponse(test_cases=[test_case], generated_count=1)
        assert response.test_cases == [test_case]
        assert response.generated_count == 1
        assert response.confidence == 0.0


class TestGenerateTestsUseCase:
    """测试GenerateTestsUseCase."""

    @pytest.fixture
    def mock_ai_generator(self) -> Mock:
        """创建模拟AI生成器."""
        generator = Mock()
        generator.provider = AIProvider.OPENAI
        generator.model = "gpt-4"
        return generator

    @pytest.fixture
    def use_case(self, mock_ai_generator: Mock) -> GenerateTestsUseCase:
        """创建用例实例."""
        return GenerateTestsUseCase(ai_generator=mock_ai_generator)

    @pytest.fixture
    def valid_project_path(self, tmp_path: Path) -> Path:
        """创建有效的项目路径."""
        return tmp_path

    def test_init_with_ai_generator(self, use_case: GenerateTestsUseCase) -> None:
        """测试使用AI生成器初始化用例."""
        assert use_case._service is not None

    def test_execute_with_target_classes(
        self, use_case: GenerateTestsUseCase, valid_project_path: Path
    ) -> None:
        """测试使用目标类执行."""
        # Arrange
        request = GenerateTestsRequest(
            project_path=valid_project_path,
            target_classes=["com.example.TestClass"],
        )

        # Mock the service methods
        mock_gen_response = MagicMock()
        mock_gen_response.test_cases = [self._create_mock_test_case()]
        mock_gen_response.explanations = ["Test generated successfully"]
        mock_gen_response.confidence = 0.9
        mock_gen_response.tokens_used = 100

        with (
            patch.object(use_case._service, "generate_tests", return_value=mock_gen_response),
            patch.object(use_case._service, "filter_by_confidence", return_value=mock_gen_response),
            patch.object(
                use_case._service, "prioritize_tests", return_value=mock_gen_response.test_cases
            ),
        ):
            # Act
            response = use_case.execute(request)

            # Assert
            assert isinstance(response, GenerateTestsResponse)
            assert response.generated_count == 1
            assert response.confidence == 0.9

    def test_execute_with_coverage_data(
        self, use_case: GenerateTestsUseCase, valid_project_path: Path
    ) -> None:
        """测试使用覆盖率数据执行."""
        # Arrange
        request = GenerateTestsRequest(
            project_path=valid_project_path,
            coverage_data={"line_coverage": 0.5},
        )

        mock_gen_response = MagicMock()
        mock_gen_response.test_cases = [self._create_mock_test_case()]
        mock_gen_response.explanations = ["Test generated for uncovered code"]
        mock_gen_response.confidence = 0.8

        with (
            patch.object(
                use_case._service, "generate_for_uncovered", return_value=mock_gen_response
            ),
            patch.object(use_case._service, "filter_by_confidence", return_value=mock_gen_response),
            patch.object(
                use_case._service, "prioritize_tests", return_value=mock_gen_response.test_cases
            ),
        ):
            # Act
            response = use_case.execute(request)

            # Assert
            assert isinstance(response, GenerateTestsResponse)
            assert response.generated_count == 1

    def test_validate_request_invalid_path(self, use_case: GenerateTestsUseCase) -> None:
        """测试验证请求：无效路径."""
        # Arrange
        request = GenerateTestsRequest(project_path=Path("/nonexistent/path"))

        # Act & Assert
        with pytest.raises(ValueError, match="项目路径不存在"):
            use_case.execute(request)

    def test_validate_request_missing_parameters(
        self, use_case: GenerateTestsUseCase, valid_project_path: Path
    ) -> None:
        """测试验证请求：缺少必要参数."""
        # Arrange
        request = GenerateTestsRequest(
            project_path=valid_project_path, target_classes=[], coverage_data=None
        )

        # Act & Assert
        with pytest.raises(ValueError, match="必须提供"):
            use_case.execute(request)

    def test_validate_request_invalid_confidence(
        self, use_case: GenerateTestsUseCase, valid_project_path: Path
    ) -> None:
        """测试验证请求：无效置信度."""
        # Arrange
        request = GenerateTestsRequest(
            project_path=valid_project_path,
            target_classes=["com.example.TestClass"],
            min_confidence=1.5,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="min_confidence必须在0和1之间"):
            use_case.execute(request)

    def _create_mock_test_case(self) -> TestCase:
        """创建模拟测试用例."""
        return TestCase(
            class_name="com.example.TestClass",
            method_name="testMethod",
            test_type=TestType.GENERATED,
            priority=TestPriority.HIGH,
            target_class="com.example.Class",
        )
