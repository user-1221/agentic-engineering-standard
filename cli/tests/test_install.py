"""Tests for aes install command."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from click.testing import CliRunner

from aes.__main__ import cli

EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"


def _make_skill(dest: Path, skill_id: str = "deploy") -> Path:
    """Create a minimal valid skill directory and return its path."""
    skill_dir = dest / "my-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / f"{skill_id}.skill.yaml").write_text(
        yaml.dump({
            "aes_skill": "1.0",
            "id": skill_id,
            "name": skill_id.title(),
            "version": "1.0.0",
            "description": f"The {skill_id} skill",
        })
    )
    (skill_dir / f"{skill_id}.md").write_text(f"# Skill: {skill_id}\nRun the {skill_id} pipeline.\n")
    return skill_dir


def _init_project(tmp_path: Path) -> Path:
    """Scaffold a minimal AES project."""
    runner = CliRunner()
    project = tmp_path / "proj"
    project.mkdir()
    result = runner.invoke(cli, [
        "init",
        "--name", "test-proj",
        "--domain", "other",
        "--language", "python",
        "--skills",
        "--workflows",
        "--no-registry",
        "--path", str(project),
    ])
    assert result.exit_code == 0, result.output
    return project


def _publish_skill(skill_dir: Path, output_dir: Path) -> Path:
    """Publish a skill and return the tarball path."""
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", str(skill_dir), "-o", str(output_dir)])
    assert result.exit_code == 0, result.output
    tarballs = list(output_dir.glob("*.tar.gz"))
    assert len(tarballs) == 1
    return tarballs[0]


def _load_agent_yaml(project: Path) -> dict:
    return yaml.safe_load((project / ".agent" / "agent.yaml").read_text()) or {}


# ---------------------------------------------------------------------------
# Tarball install
# ---------------------------------------------------------------------------

class TestTarballInstall:

    def test_install_tarball_round_trip(self, tmp_path: Path) -> None:
        """publish -> install -> validate passes, files in vendor, registered."""
        project = _init_project(tmp_path)
        skill_dir = _make_skill(tmp_path)
        tarball = _publish_skill(skill_dir, tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["install", str(tarball), "--path", str(project)])
        assert result.exit_code == 0, result.output
        assert "Installed skill" in result.output

        # Files in vendor
        vendor = project / ".agent" / "skills" / "vendor" / "deploy"
        assert vendor.exists()
        assert (vendor / "deploy.skill.yaml").exists()
        assert (vendor / "deploy.md").exists()

        # Validate passes
        result = runner.invoke(cli, ["validate", str(project)])
        assert result.exit_code == 0, result.output

    def test_install_tarball_registers_in_agent_yaml(self, tmp_path: Path) -> None:
        project = _init_project(tmp_path)
        skill_dir = _make_skill(tmp_path)
        tarball = _publish_skill(skill_dir, tmp_path)

        runner = CliRunner()
        runner.invoke(cli, ["install", str(tarball), "--path", str(project)])

        data = _load_agent_yaml(project)
        skills = data.get("skills", [])
        deploy_entries = [s for s in skills if s["id"] == "deploy"]
        assert len(deploy_entries) == 1
        entry = deploy_entries[0]
        assert entry["manifest"] == "skills/vendor/deploy/deploy.skill.yaml"
        assert entry["runbook"] == "skills/vendor/deploy/deploy.md"

    def test_install_tarball_refuses_overwrite(self, tmp_path: Path) -> None:
        project = _init_project(tmp_path)
        skill_dir = _make_skill(tmp_path)
        tarball = _publish_skill(skill_dir, tmp_path)

        runner = CliRunner()
        runner.invoke(cli, ["install", str(tarball), "--path", str(project)])
        result = runner.invoke(cli, ["install", str(tarball), "--path", str(project)])
        assert result.exit_code != 0
        assert "already installed" in result.output or "--force" in result.output

    def test_install_tarball_force_overwrites(self, tmp_path: Path) -> None:
        project = _init_project(tmp_path)
        skill_dir = _make_skill(tmp_path)
        tarball = _publish_skill(skill_dir, tmp_path)

        runner = CliRunner()
        runner.invoke(cli, ["install", str(tarball), "--path", str(project)])
        result = runner.invoke(cli, ["install", str(tarball), "--path", str(project), "--force"])
        assert result.exit_code == 0, result.output
        assert "Installed skill" in result.output

    def test_install_tarball_nonexistent(self, tmp_path: Path) -> None:
        project = _init_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["install", str(tmp_path / "nope.tar.gz"), "--path", str(project)])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Local directory install
# ---------------------------------------------------------------------------

class TestLocalInstall:

    def test_install_local_directory(self, tmp_path: Path) -> None:
        """Bare directory path auto-detected and installed."""
        project = _init_project(tmp_path)
        skill_dir = _make_skill(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["install", str(skill_dir), "--path", str(project)])
        assert result.exit_code == 0, result.output
        assert "Installed skill" in result.output

        vendor = project / ".agent" / "skills" / "vendor" / "deploy"
        assert vendor.exists()
        assert (vendor / "deploy.skill.yaml").exists()

    def test_install_local_prefix(self, tmp_path: Path) -> None:
        """local: prefix stripped and works."""
        project = _init_project(tmp_path)
        skill_dir = _make_skill(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["install", f"local:{skill_dir}", "--path", str(project)])
        assert result.exit_code == 0, result.output
        assert "Installed skill" in result.output

    def test_install_local_missing_manifest(self, tmp_path: Path) -> None:
        """Clean error when directory has no manifest."""
        project = _init_project(tmp_path)
        empty_dir = tmp_path / "empty-skill"
        empty_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, ["install", str(empty_dir), "--path", str(project)])
        assert result.exit_code != 0
        assert "No skill manifest" in result.output

    def test_install_local_validates(self, tmp_path: Path) -> None:
        """Installed skill passes validation."""
        project = _init_project(tmp_path)
        skill_dir = _make_skill(tmp_path)

        runner = CliRunner()
        runner.invoke(cli, ["install", str(skill_dir), "--path", str(project)])
        result = runner.invoke(cli, ["validate", str(project)])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Dependency install (no args)
# ---------------------------------------------------------------------------

class TestDepsInstall:

    def test_install_deps_local_sources(self, tmp_path: Path) -> None:
        """aes install reads deps, installs local ones."""
        project = _init_project(tmp_path)
        skill_dir = _make_skill(tmp_path, skill_id="monitoring")

        # Add dependency to agent.yaml
        data = _load_agent_yaml(project)
        data.setdefault("dependencies", {})["skills"] = {
            "monitoring": f"local:{skill_dir}",
        }
        (project / ".agent" / "agent.yaml").write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False)
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["install", "--path", str(project)])
        assert result.exit_code == 0, result.output
        assert "Installed" in result.output
        assert (project / ".agent" / "skills" / "vendor" / "monitoring").exists()

    def test_install_deps_skips_unsupported(self, tmp_path: Path) -> None:
        """Registry/git deps print skip, don't crash."""
        project = _init_project(tmp_path)

        data = _load_agent_yaml(project)
        data.setdefault("dependencies", {})["skills"] = {
            "from-hub": "aes-hub/some-skill@1.0.0",
            "from-git": "github:org/repo@main",
        }
        (project / ".agent" / "agent.yaml").write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False)
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["install", "--path", str(project)])
        assert result.exit_code == 0, result.output
        assert "Skipped" in result.output
        assert "not yet supported" in result.output

    def test_install_deps_no_deps(self, tmp_path: Path) -> None:
        """Clean exit when no deps."""
        project = _init_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["install", "--path", str(project)])
        assert result.exit_code == 0, result.output
        assert "No skill dependencies" in result.output


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_install_no_duplicate_registration(self, tmp_path: Path) -> None:
        """Install same skill twice with --force -> one entry, not two."""
        project = _init_project(tmp_path)
        skill_dir = _make_skill(tmp_path)

        runner = CliRunner()
        runner.invoke(cli, ["install", str(skill_dir), "--path", str(project)])
        runner.invoke(cli, ["install", str(skill_dir), "--path", str(project), "--force"])

        data = _load_agent_yaml(project)
        skills = data.get("skills", [])
        deploy_entries = [s for s in skills if s["id"] == "deploy"]
        assert len(deploy_entries) == 1

    def test_installed_skill_in_sync_output(self, tmp_path: Path) -> None:
        """install -> sync -> runbook appears in CLAUDE.md."""
        project = _init_project(tmp_path)
        skill_dir = _make_skill(tmp_path)

        runner = CliRunner()
        runner.invoke(cli, ["install", str(skill_dir), "--path", str(project)])

        # Sync to Claude target
        result = runner.invoke(cli, ["sync", str(project), "-t", "claude", "--force"])
        assert result.exit_code == 0, result.output

        claude_md = project / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "deploy" in content.lower()
