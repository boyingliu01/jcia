"""YAML 配置管理实现."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class YamlConfigManager:
    """负责加载与访问 YAML 配置的管理器."""

    def __init__(self, default_path: str | Path | None = None) -> None:
        self._default_path = Path(default_path) if default_path else None
        self._config: dict[str, Any] | None = None

    def load(
        self,
        path: str | Path | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """加载 YAML 配置并应用覆盖项.

        Args:
            path: 显式配置文件路径，优先级高于默认路径
            overrides: 需要应用的覆盖配置，将深度合并

        Returns:
            dict[str, Any]: 加载并合并后的配置

        Raises:
            FileNotFoundError: 当文件不存在时
        """

        config_path = Path(path) if path else self._default_path
        if config_path is None:
            raise FileNotFoundError("配置文件路径未提供")
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with config_path.open("r", encoding="utf-8") as file:
            loaded: dict[str, Any] | None = yaml.safe_load(file)

        self._config = loaded or {}

        if overrides:
            self._config = self._deep_merge(self._config, overrides)

        return deepcopy(self._config)

    def get(self, key: str, default: Any | None = None) -> Any | None:
        """按点分隔键获取配置值."""

        if self._config is None:
            return default

        current: Any = self._config
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    @staticmethod
    def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        """对字典执行深度合并，优先使用 overrides 的值."""

        merged = deepcopy(base)
        for key, value in overrides.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = YamlConfigManager._deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
