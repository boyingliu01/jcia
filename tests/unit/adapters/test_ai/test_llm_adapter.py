"""LLM 适配器工厂测试."""

import pytest

from jcia.adapters.ai.llm_adapter import LLMAdapterFactory
from jcia.adapters.ai.volcengine_adapter import VolcengineAdapter
from jcia.core.interfaces.ai_service import AIProvider


class TestLLMAdapterFactory:
    """LLMAdapterFactory 测试类."""

    def test_create_volcengine_adapter_with_enum(self) -> None:
        """测试使用枚举创建火山引擎适配器."""
        adapter = LLMAdapterFactory.create_adapter(
            provider=AIProvider.VOLCENGINE,
            access_key="test_ak",
            secret_key="test_sk",  # noqa: S106
            app_id="test_app",
        )

        assert isinstance(adapter, VolcengineAdapter)
        assert adapter.provider == AIProvider.VOLCENGINE

    def test_create_volcengine_adapter_with_string(self) -> None:
        """测试使用字符串创建火山引擎适配器."""
        adapter = LLMAdapterFactory.create_adapter(
            provider="volcengine",
            access_key="test_ak",
            secret_key="test_sk",  # noqa: S106
            app_id="test_app",
        )

        assert isinstance(adapter, VolcengineAdapter)

    def test_create_unsupported_provider_raises_error(self) -> None:
        """测试创建不支持的提供商抛出错误."""
        with pytest.raises(ValueError, match="Unsupported AI provider: openai"):
            LLMAdapterFactory.create_adapter(provider="openai")
