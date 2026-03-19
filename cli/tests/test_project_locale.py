"""Tests for per-project locale configuration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from aes.global_config import get_project_locale


class TestGetProjectLocale:
    def test_returns_locale_from_local_yaml(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        local_yaml = agent_dir / "local.yaml"
        local_yaml.write_text(yaml.dump({"locale": "ja"}))

        assert get_project_locale(tmp_path) == "ja"

    def test_returns_none_when_no_local_yaml(self, tmp_path):
        assert get_project_locale(tmp_path) is None

    def test_returns_none_when_no_locale_field(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        local_yaml = agent_dir / "local.yaml"
        local_yaml.write_text(yaml.dump({"permissions": {}}))

        assert get_project_locale(tmp_path) is None

    def test_returns_none_for_empty_locale(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        local_yaml = agent_dir / "local.yaml"
        local_yaml.write_text(yaml.dump({"locale": ""}))

        assert get_project_locale(tmp_path) is None

    def test_returns_none_for_invalid_yaml(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        local_yaml = agent_dir / "local.yaml"
        local_yaml.write_text(": : invalid yaml [[[")

        assert get_project_locale(tmp_path) is None


class TestLocaleResolutionChain:
    """Test the priority chain in cli() group callback."""

    def test_lang_flag_overrides_project_locale(self, tmp_path):
        from click.testing import CliRunner
        from aes.__main__ import cli

        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "local.yaml").write_text(yaml.dump({"locale": "ja"}))

        with patch("aes.__main__.os.environ.get", return_value=None), \
             patch("aes.i18n.init_locale") as mock_init:
            runner = CliRunner()
            runner.invoke(cli, ["--lang", "en", "validate", str(tmp_path)])
            mock_init.assert_called_with("en")

    def test_project_locale_used_when_no_flag_or_env(self, tmp_path):
        from click.testing import CliRunner
        from aes.__main__ import cli

        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "local.yaml").write_text(yaml.dump({"locale": "ja"}))

        with patch("os.getcwd", return_value=str(tmp_path)), \
             patch("aes.global_config.get_project_locale", return_value="ja") as mock_proj, \
             patch("aes.i18n.init_locale") as mock_init:
            runner = CliRunner(env={"AES_LANG": None})
            runner.invoke(cli, ["validate", str(tmp_path)])
            mock_proj.assert_called_once()
            # Project locale should be used
            mock_init.assert_any_call("ja")

    def test_global_config_used_when_no_project_locale(self, tmp_path):
        from click.testing import CliRunner
        from aes.__main__ import cli

        with patch("aes.global_config.get_project_locale", return_value=None), \
             patch("aes.global_config.get_locale", return_value="en"), \
             patch("aes.i18n.init_locale") as mock_init:
            runner = CliRunner(env={"AES_LANG": None})
            runner.invoke(cli, ["validate", str(tmp_path)])
            # Should fall through to init_locale() (uses global config internally)
            mock_init.assert_called_with()
