"""YamlConfigManager 配置管理单元测试."""

from pathlib import Path

import pytest

from jcia.infrastructure.config.config_manager import YamlConfigManager


class TestYamlConfigManager:
    """YamlConfigManager 行为测试."""

    def test_load_reads_yaml_and_get_by_key(self, tmp_path: Path) -> None:
        """应能读取 YAML 并通过点分隔键访问."""
        config_file = tmp_path / ".jcia.yaml"
        config_file.write_text(
            """
project:
  name: demo
analysis:
  change_detection:
    ignore_patterns:
      - "*.md"
""".lstrip(),
            encoding="utf-8",
        )

        manager = YamlConfigManager(default_path=config_file)

        loaded = manager.load()

        assert loaded["project"]["name"] == "demo"
        assert manager.get("project.name") == "demo"
        assert manager.get("analysis.change_detection.ignore_patterns") == ["*.md"]

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        """找不到文件时抛出 FileNotFoundError."""
        manager = YamlConfigManager(default_path=tmp_path / "missing.yaml")

        with pytest.raises(FileNotFoundError):
            manager.load()

    def test_overrides_apply_deep_merge(self, tmp_path: Path) -> None:
        """覆盖配置应做深度合并，不丢失原值."""
        config_file = tmp_path / ".jcia.yaml"
        config_file.write_text(
            """
testing:
  test_selection:
    enabled: true
  regression:
    baseline_branch: main
""".lstrip(),
            encoding="utf-8",
        )
        overrides = {
            "testing": {
                "test_selection": {"enabled": False},
                "regression": {"baseline_branch": "develop"},
            }
        }

        manager = YamlConfigManager(default_path=config_file)
        merged = manager.load(overrides=overrides)

        assert merged["testing"]["test_selection"]["enabled"] is False
        assert merged["testing"]["regression"]["baseline_branch"] == "develop"

    def test_get_returns_default_when_missing(self, tmp_path: Path) -> None:
        """缺失键应返回默认值."""
        config_file = tmp_path / ".jcia.yaml"
        config_file.write_text("project:\n  name: demo\n", encoding="utf-8")

        manager = YamlConfigManager(default_path=config_file)
        manager.load()

        assert manager.get("report.output_dir", "./reports") == "./reports"
