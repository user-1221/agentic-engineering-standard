"""Tests for aes bom command."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from aes.__main__ import cli


def _make_project_with_bom(tmp_path: Path, bom_data: dict) -> Path:
    """Create a minimal .agent/ project with a bom.yaml."""
    project = tmp_path / "project"
    project.mkdir()
    agent_dir = project / ".agent"
    agent_dir.mkdir()

    manifest = {
        "aes": "1.2",
        "name": "bom-test",
        "version": "1.0.0",
        "description": "Test project with BOM",
        "runtime": {"language": "python"},
        "agent": {"instructions": "instructions.md"},
    }
    (agent_dir / "agent.yaml").write_text(yaml.dump(manifest))
    (agent_dir / "instructions.md").write_text("# Instructions\n")
    (agent_dir / "bom.yaml").write_text(yaml.dump(bom_data, default_flow_style=False))

    return project


class TestBomCommand:
    def test_bom_displays_models(self, tmp_path: Path) -> None:
        bom = {
            "aes_bom": "1.2",
            "models": [
                {"name": "claude-sonnet-4", "provider": "anthropic", "purpose": "primary"},
            ],
        }
        project = _make_project_with_bom(tmp_path, bom)
        runner = CliRunner()
        result = runner.invoke(cli, ["bom", str(project)])
        assert result.exit_code == 0
        assert "claude-sonnet-4" in result.output
        assert "anthropic" in result.output

    def test_bom_displays_frameworks(self, tmp_path: Path) -> None:
        bom = {
            "aes_bom": "1.2",
            "frameworks": [
                {"name": "catboost", "version": "1.2.2", "license": "Apache-2.0"},
            ],
        }
        project = _make_project_with_bom(tmp_path, bom)
        runner = CliRunner()
        result = runner.invoke(cli, ["bom", str(project)])
        assert result.exit_code == 0
        assert "catboost" in result.output
        assert "1.2.2" in result.output

    def test_bom_displays_tools(self, tmp_path: Path) -> None:
        bom = {
            "aes_bom": "1.2",
            "tools": [
                {"name": "fetch", "type": "mcp-server", "version": "1.0.0"},
            ],
        }
        project = _make_project_with_bom(tmp_path, bom)
        runner = CliRunner()
        result = runner.invoke(cli, ["bom", str(project)])
        assert result.exit_code == 0
        assert "fetch" in result.output
        assert "mcp-server" in result.output

    def test_bom_displays_data_sources(self, tmp_path: Path) -> None:
        bom = {
            "aes_bom": "1.2",
            "data_sources": [
                {"name": "openml", "type": "api", "uri": "https://openml.org"},
            ],
        }
        project = _make_project_with_bom(tmp_path, bom)
        runner = CliRunner()
        result = runner.invoke(cli, ["bom", str(project)])
        assert result.exit_code == 0
        assert "openml" in result.output

    def test_bom_no_bom_file(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        project.mkdir()
        agent_dir = project / ".agent"
        agent_dir.mkdir()
        manifest = {
            "aes": "1.2",
            "name": "no-bom",
            "version": "1.0.0",
            "description": "No BOM",
            "runtime": {"language": "python"},
            "agent": {"instructions": "instructions.md"},
        }
        (agent_dir / "agent.yaml").write_text(yaml.dump(manifest))
        (agent_dir / "instructions.md").write_text("# Instructions\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["bom", str(project)])
        assert result.exit_code == 0
        assert "bom.yaml" in result.output.lower() or "not found" in result.output.lower()

    def test_bom_no_agent_dir(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["bom", str(tmp_path)])
        assert result.exit_code == 1

    def test_bom_summary_counts(self, tmp_path: Path) -> None:
        bom = {
            "aes_bom": "1.2",
            "models": [
                {"name": "m1", "provider": "p1"},
                {"name": "m2", "provider": "p2"},
            ],
            "frameworks": [{"name": "f1"}],
            "tools": [{"name": "t1", "type": "cli"}],
            "data_sources": [{"name": "d1", "type": "api"}],
        }
        project = _make_project_with_bom(tmp_path, bom)
        runner = CliRunner()
        result = runner.invoke(cli, ["bom", str(project)])
        assert result.exit_code == 0
        assert "2" in result.output  # 2 models
