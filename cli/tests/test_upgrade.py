"""Tests for aes upgrade command."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from aes.__main__ import cli


def _make_project(tmp_path: Path, aes_version: str = "1.0", commands: list = None) -> Path:
    """Create a minimal .agent/ project at the given spec version."""
    project = tmp_path / "project"
    project.mkdir()
    agent_dir = project / ".agent"
    agent_dir.mkdir()
    (agent_dir / "commands").mkdir()

    manifest = {
        "aes": aes_version,
        "name": "test-project",
        "version": "0.1.0",
        "description": "Test project",
        "runtime": {"language": "python"},
        "agent": {"instructions": "instructions.md"},
    }
    if commands is not None:
        manifest["commands"] = commands
    else:
        manifest["commands"] = [
            {
                "id": "setup",
                "path": "commands/setup.md",
                "trigger": "/setup",
                "description": "Setup command",
            }
        ]

    with open(agent_dir / "agent.yaml", "w") as f:
        yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)

    (agent_dir / "instructions.md").write_text("# Instructions\n")
    (agent_dir / "commands" / "setup.md").write_text("# Setup\n")

    return project


def _make_v11_project(tmp_path: Path, commands: list = None) -> Path:
    """Create a v1.1 project (has /memory command but no bom.yaml)."""
    project = tmp_path / "project"
    project.mkdir()
    agent_dir = project / ".agent"
    agent_dir.mkdir()
    (agent_dir / "commands").mkdir()

    manifest = {
        "aes": "1.1",
        "name": "test-v11",
        "version": "0.1.0",
        "description": "v1.1 test project",
        "runtime": {"language": "python"},
        "agent": {"instructions": "instructions.md"},
    }
    if commands is not None:
        manifest["commands"] = commands
    else:
        manifest["commands"] = [
            {
                "id": "setup",
                "path": "commands/setup.md",
                "trigger": "/setup",
                "description": "Setup command",
            },
            {
                "id": "memory",
                "path": "commands/memory.md",
                "trigger": "/memory",
                "description": "Memory command",
            },
        ]

    with open(agent_dir / "agent.yaml", "w") as f:
        yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)

    (agent_dir / "instructions.md").write_text("# Instructions\n")
    (agent_dir / "commands" / "setup.md").write_text("# Setup\n")
    (agent_dir / "commands" / "memory.md").write_text("# Memory\n")

    return project


class TestUpgradeDryRun:
    """Test upgrade plan display (default dry-run behavior)."""

    def test_upgrade_detects_outdated_project(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, aes_version="1.0")
        runner = CliRunner()
        result = runner.invoke(cli, ["upgrade", str(project)])
        assert result.exit_code == 0
        assert "1.0" in result.output
        assert "1.1" in result.output
        assert "/memory" in result.output
        assert "aes upgrade --apply" in result.output

    def test_upgrade_up_to_date(self, tmp_path: Path) -> None:
        project = _make_project(
            tmp_path,
            aes_version="1.2",
            commands=[
                {
                    "id": "setup",
                    "path": "commands/setup.md",
                    "trigger": "/setup",
                    "description": "Setup",
                },
                {
                    "id": "memory",
                    "path": "commands/memory.md",
                    "trigger": "/memory",
                    "description": "Memory",
                },
            ],
        )
        # Create the memory command file too
        (project / ".agent" / "commands" / "memory.md").write_text("# Memory\n")
        # Create bom.yaml too (required for v1.2)
        (project / ".agent" / "bom.yaml").write_text("aes_bom: '1.2'\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["upgrade", str(project)])
        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_upgrade_dry_run_no_file_changes(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, aes_version="1.0")
        runner = CliRunner()
        runner.invoke(cli, ["upgrade", str(project)])

        # File should NOT be created in dry-run mode
        assert not (project / ".agent" / "commands" / "memory.md").exists()

        # agent.yaml should NOT be modified
        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)
        assert manifest["aes"] == "1.0"

    def test_upgrade_no_agent_dir(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["upgrade", str(tmp_path)])
        assert result.exit_code == 1
        assert "aes init" in result.output


class TestUpgradeApply:
    """Test upgrade --apply behavior."""

    def test_upgrade_apply_creates_file(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, aes_version="1.0")
        runner = CliRunner()
        result = runner.invoke(cli, ["upgrade", str(project), "--apply"])
        assert result.exit_code == 0

        # Memory command file should be created
        memory_cmd = project / ".agent" / "commands" / "memory.md"
        assert memory_cmd.exists()
        content = memory_cmd.read_text()
        assert "memory" in content.lower()

    def test_upgrade_apply_updates_manifest(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, aes_version="1.0")
        runner = CliRunner()
        runner.invoke(cli, ["upgrade", str(project), "--apply"])

        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)

        # Version bumped to latest (1.2)
        assert manifest["aes"] == "1.2"

        # Memory command entry added
        cmd_ids = [c["id"] for c in manifest.get("commands", [])]
        assert "memory" in cmd_ids

    def test_upgrade_preserves_existing_commands(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, aes_version="1.0")
        runner = CliRunner()
        runner.invoke(cli, ["upgrade", str(project), "--apply"])

        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)

        cmd_ids = [c["id"] for c in manifest.get("commands", [])]
        # Original setup command should still be present
        assert "setup" in cmd_ids
        # New memory command added
        assert "memory" in cmd_ids

    def test_upgrade_idempotent(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, aes_version="1.0")
        runner = CliRunner()

        # First apply
        runner.invoke(cli, ["upgrade", str(project), "--apply"])

        # Second apply — should be a no-op
        result = runner.invoke(cli, ["upgrade", str(project), "--apply"])
        assert result.exit_code == 0
        assert "up to date" in result.output

        # Memory command should appear only once
        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)
        memory_count = sum(
            1 for c in manifest.get("commands", []) if c.get("id") == "memory"
        )
        assert memory_count == 1

    def test_upgrade_skips_existing_file(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, aes_version="1.0")

        # Manually create the memory command file with custom content
        custom_content = "# My custom memory command\n"
        (project / ".agent" / "commands" / "memory.md").write_text(custom_content)

        runner = CliRunner()
        runner.invoke(cli, ["upgrade", str(project), "--apply"])

        # File should NOT be overwritten
        content = (project / ".agent" / "commands" / "memory.md").read_text()
        assert content == custom_content

        # But manifest entry should still be added
        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)
        cmd_ids = [c["id"] for c in manifest.get("commands", [])]
        assert "memory" in cmd_ids

    def test_upgrade_skips_existing_manifest_entry(self, tmp_path: Path) -> None:
        """If manifest already has the entry but file is missing, create file only."""
        project = _make_project(
            tmp_path,
            aes_version="1.0",
            commands=[
                {
                    "id": "setup",
                    "path": "commands/setup.md",
                    "trigger": "/setup",
                    "description": "Setup",
                },
                {
                    "id": "memory",
                    "path": "commands/memory.md",
                    "trigger": "/memory",
                    "description": "Memory",
                },
            ],
        )

        runner = CliRunner()
        runner.invoke(cli, ["upgrade", str(project), "--apply"])

        # File should be created
        assert (project / ".agent" / "commands" / "memory.md").exists()

        # Entry should NOT be duplicated
        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)
        memory_count = sum(
            1 for c in manifest.get("commands", []) if c.get("id") == "memory"
        )
        assert memory_count == 1

    def test_upgrade_auto_syncs(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, aes_version="1.0")
        runner = CliRunner()
        runner.invoke(cli, ["upgrade", str(project), "--apply"])

        # CLAUDE.md should be created by auto-sync
        assert (project / "CLAUDE.md").exists()

    def test_upgrade_v10_to_v12_creates_both(self, tmp_path: Path) -> None:
        """Upgrading from 1.0 to 1.2 should apply both migrations."""
        project = _make_project(tmp_path, aes_version="1.0")
        runner = CliRunner()
        result = runner.invoke(cli, ["upgrade", str(project), "--apply"])
        assert result.exit_code == 0

        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)

        # Version should be latest
        assert manifest["aes"] == "1.2"

        # Memory command should be added
        cmd_ids = [c["id"] for c in manifest.get("commands", [])]
        assert "memory" in cmd_ids

        # bom.yaml should be created
        assert (project / ".agent" / "bom.yaml").exists()

    def test_upgrade_no_aes_field_defaults_to_1_0(self, tmp_path: Path) -> None:
        """Projects without an aes field should be treated as 1.0."""
        project = _make_project(tmp_path, aes_version="1.0")

        # Remove the aes field
        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)
        del manifest["aes"]
        with open(project / ".agent" / "agent.yaml", "w") as f:
            yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)

        runner = CliRunner()
        result = runner.invoke(cli, ["upgrade", str(project)])
        assert result.exit_code == 0
        # Should detect as 1.0 and offer upgrade
        assert "1.0" in result.output
        assert "/memory" in result.output


# ---------------------------------------------------------------------------
# v1.1 → v1.2 migration tests
# ---------------------------------------------------------------------------


class TestUpgradeV11ToV12DryRun:
    """Test 1.1→1.2 upgrade plan display."""

    def test_upgrade_from_v11_detects_bom(self, tmp_path: Path) -> None:
        project = _make_v11_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["upgrade", str(project)])
        assert result.exit_code == 0
        assert "1.1" in result.output
        assert "1.2" in result.output
        assert "bom.yaml" in result.output

    def test_upgrade_v11_dry_run_no_changes(self, tmp_path: Path) -> None:
        project = _make_v11_project(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["upgrade", str(project)])

        # bom.yaml should NOT exist in dry-run
        assert not (project / ".agent" / "bom.yaml").exists()

        # Version should NOT be bumped
        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)
        assert manifest["aes"] == "1.1"


class TestUpgradeV11ToV12Apply:
    """Test 1.1→1.2 upgrade --apply."""

    def test_upgrade_creates_bom(self, tmp_path: Path) -> None:
        project = _make_v11_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["upgrade", str(project), "--apply"])
        assert result.exit_code == 0

        # bom.yaml should be created
        bom_path = project / ".agent" / "bom.yaml"
        assert bom_path.exists()

    def test_upgrade_bumps_to_v12(self, tmp_path: Path) -> None:
        project = _make_v11_project(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["upgrade", str(project), "--apply"])

        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)
        assert manifest["aes"] == "1.2"

    def test_upgrade_preserves_existing_commands(self, tmp_path: Path) -> None:
        project = _make_v11_project(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["upgrade", str(project), "--apply"])

        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)
        cmd_ids = [c["id"] for c in manifest.get("commands", [])]
        assert "setup" in cmd_ids
        assert "memory" in cmd_ids

    def test_upgrade_v12_idempotent(self, tmp_path: Path) -> None:
        project = _make_v11_project(tmp_path)
        runner = CliRunner()

        # First apply
        runner.invoke(cli, ["upgrade", str(project), "--apply"])

        # Second apply — should be up to date
        result = runner.invoke(cli, ["upgrade", str(project), "--apply"])
        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_upgrade_skips_existing_bom(self, tmp_path: Path) -> None:
        project = _make_v11_project(tmp_path)

        # Create custom bom.yaml
        custom_bom = "aes_bom: '1.2'\nmodels:\n  - name: custom\n    provider: custom\n"
        (project / ".agent" / "bom.yaml").write_text(custom_bom)

        runner = CliRunner()
        runner.invoke(cli, ["upgrade", str(project), "--apply"])

        # Custom content should be preserved
        content = (project / ".agent" / "bom.yaml").read_text()
        assert "custom" in content

    def test_full_v10_to_v12_upgrade(self, tmp_path: Path) -> None:
        """v1.0 project upgrades all the way to v1.2 in one pass."""
        project = _make_project(tmp_path, aes_version="1.0")
        runner = CliRunner()
        result = runner.invoke(cli, ["upgrade", str(project), "--apply"])
        assert result.exit_code == 0

        with open(project / ".agent" / "agent.yaml") as f:
            manifest = yaml.safe_load(f)

        # Should be at latest version
        assert manifest["aes"] == "1.2"

        # Memory command should exist (from 1.0→1.1)
        cmd_ids = [c["id"] for c in manifest.get("commands", [])]
        assert "memory" in cmd_ids

        # bom.yaml should exist (from 1.1→1.2)
        assert (project / ".agent" / "bom.yaml").exists()
