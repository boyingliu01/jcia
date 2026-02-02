"""LLM 适配器工厂.

提供对不同 AI 服务提供商的统一访问。
"""

from typing import Any

from jcia.adapters.ai.volcengine_adapter import VolcengineAdapter
from jcia.core.interfaces.ai_service import AIAnalyzer, AIProvider, AITestGenerator


class LLMAdapterFactory:
    """LLM 适配器工厂类."""

    @staticmethod
    def create_adapter(
        provider: AIProvider | str,
        **kwargs: Any,
    ) -> AITestGenerator | AIAnalyzer:
        """根据提供商创建对应的适配器实例.

        Args:
            provider: AI 服务提供商
            **kwargs: 适配器初始化参数

        Returns:
            AITestGenerator | AIAnalyzer: 适配器实例

        Raises:
            ValueError: 不支持的提供商
        """
        provider_val = provider.value if isinstance(provider, AIProvider) else str(provider).lower()

        if provider_val == AIProvider.VOLCENGINE.value:
            return VolcengineAdapter(**kwargs)

        raise ValueError(f"Unsupported AI provider: {provider_val}")
