"""Tests for aes status command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from aes.__main__ import cli


def _init_and_sync(tmp_path: Path) -> Path:
    """Scaffold a project and sync it so status has something to report."""
    project = tmp_path / "proj"
    project.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init",
        "--name", "status-test",
        "--domain", "other",
        "--language", "python",
        "--path", str(project),
    ])
    assert result.exit_code == 0, result.output
    # init auto-syncs, so .aes-sync.json should exist
    assert (project / ".aes-sync.json").exists()
    return project


class TestStatusUpToDate:

    def test_status_up_to_date(self, tmp_path: Path) -> None:
        """Freshly synced project reports up to date."""
        project = _init_and_sync(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["status", str(project)])
        assert result.exit_code == 0, result.output
        assert "up to date" in result.output.lower()

    def test_status_no_sync_history(self, tmp_path: Path) -> None:
        """Project with no .aes-sync.json shows helpful message."""
        project = tmp_path / "proj"
        project.mkdir()
        runner = CliRunner()
        runner.invoke(cli, [
            "init",
            "--name", "no-sync",
            "--domain", "other",
            "--language", "python",
            "--path", str(project),
        ])
        # Remove sync manifest
        sync_file = project / ".aes-sync.json"
        if sync_file.exists():
            sync_file.unlink()

        result = runner.invoke(cli, ["status", str(project)])
        assert result.exit_code == 0, result.output
        assert "No sync history" in result.output


class TestStatusNeedsSync:

    def test_status_detects_source_change(self, tmp_path: Path) -> None:
        """Editing .agent/instructions.md causes status to report needs sync."""
        project = _init_and_sync(tmp_path)

        # Edit instructions
        instructions = project / ".agent" / "instructions.md"
        instructions.write_text(instructions.read_text() + "\n## New Section\nNew content.\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["status", str(project)])
        assert result.exit_code == 0, result.output
        assert "needs sync" in result.output.lower() or "aes sync" in result.output

    def test_status_detects_deleted_output(self, tmp_path: Path) -> None:
        """Deleting a synced output file is reported."""
        project = _init_and_sync(tmp_path)

        # Delete CLAUDE.md
        claude_md = project / "CLAUDE.md"
        if claude_md.exists():
            claude_md.unlink()

        runner = CliRunner()
        result = runner.invoke(cli, ["status", str(project)])
        assert result.exit_code == 0, result.output
        assert "missing" in result.output.lower() or "aes sync" in result.output

    def test_status_after_resync_is_clean(self, tmp_path: Path) -> None:
        """Edit source -> status shows stale -> sync -> status shows clean."""
        project = _init_and_sync(tmp_path)

        # Edit instructions
        instructions = project / ".agent" / "instructions.md"
        instructions.write_text(instructions.read_text() + "\nChanged.\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["status", str(project)])
        assert "aes sync" in result.output

        # Re-sync
        runner.invoke(cli, ["sync", str(project), "--force"])

        result = runner.invoke(cli, ["status", str(project)])
        assert result.exit_code == 0, result.output
        assert "up to date" in result.output.lower()


class TestStatusNoAgent:

    def test_status_no_agent_dir(self, tmp_path: Path) -> None:
        """Clean error when no .agent/ exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", str(tmp_path)])
        assert result.exit_code != 0
        assert "No .agent/" in result.output or "Error" in result.output
