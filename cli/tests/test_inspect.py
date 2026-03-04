"""Tests for aes inspect command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from aes.__main__ import cli


EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"


class TestInspect:
    def test_inspect_ml_pipeline(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["inspect", str(EXAMPLES_DIR / "ml-pipeline")])
        assert result.exit_code == 0
        assert "ml-model-factory" in result.output
        assert "v2.1.0" in result.output
        assert "discover" in result.output
        assert "train" in result.output
        assert "dataset-pipeline" in result.output

    def test_inspect_web_app(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["inspect", str(EXAMPLES_DIR / "web-app")])
        assert result.exit_code == 0
        assert "saas-dashboard" in result.output
        assert "scaffold" in result.output
        assert "feature-lifecycle" in result.output

    def test_inspect_devops(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["inspect", str(EXAMPLES_DIR / "devops")])
        assert result.exit_code == 0
        assert "infra-autopilot" in result.output
        assert "provision" in result.output
        assert "rollback" in result.output

    def test_inspect_no_agent_dir(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["inspect", str(tmp_path)])
        assert result.exit_code == 1
        assert "No .agent/" in result.output

    def test_inspect_shows_summary(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["inspect", str(EXAMPLES_DIR / "ml-pipeline")])
        assert "Summary" in result.output
        assert "Skills:" in result.output
        assert "Registries:" in result.output
        assert "Workflows:" in result.output
