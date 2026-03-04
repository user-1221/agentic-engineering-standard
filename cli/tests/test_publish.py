"""Tests for aes publish command."""

from __future__ import annotations

import shutil
import tarfile
from pathlib import Path
from typing import Set

import yaml
from click.testing import CliRunner

from aes.__main__ import cli

EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"


def _tarball_members(tarball: Path) -> Set[str]:
    """Return set of member names in a tarball."""
    with tarfile.open(tarball, "r:gz") as tar:
        return set(tar.getnames())


def _make_skill(dest: Path, skill_id: str = "deploy") -> Path:
    """Create a minimal valid skill directory."""
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
    (skill_dir / f"{skill_id}.md").write_text(f"# Skill: {skill_id}\nRun it.\n")
    return skill_dir


class TestPublishExplicitPath:
    """Original behavior: publish a specific directory."""

    def test_publish_skill_dir(self, tmp_path: Path) -> None:
        skill_dir = _make_skill(tmp_path)
        out = tmp_path / "out"
        out.mkdir()
        runner = CliRunner()
        result = runner.invoke(cli, ["publish", str(skill_dir), "-o", str(out)])
        assert result.exit_code == 0, result.output
        assert "Published" in result.output
        tarballs = list(out.glob("*.tar.gz"))
        assert len(tarballs) == 1
        assert tarballs[0].name == "deploy-1.0.0.tar.gz"


class TestPublishFromProject:
    """No-arg publish reads agent.yaml and packages all skills."""

    def test_publish_no_args_from_project(self, tmp_path: Path) -> None:
        """Publishes all skills from an example project."""
        project = tmp_path / "project"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", project)
        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, ["publish", "-o", str(out), "--path", str(project)])
        assert result.exit_code == 0, result.output

        tarballs = sorted(p.name for p in out.glob("*.tar.gz"))
        # ml-pipeline has 3 skills: discover, examine, train
        assert len(tarballs) == 3
        assert "discover-1.0.0.tar.gz" in tarballs
        assert "examine-1.0.0.tar.gz" in tarballs
        assert "train-1.0.0.tar.gz" in tarballs

    def test_publish_single_skill_flag(self, tmp_path: Path) -> None:
        """--skill flag publishes only one."""
        project = tmp_path / "project"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", project)
        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, [
            "publish", "-o", str(out), "--path", str(project), "--skill", "train",
        ])
        assert result.exit_code == 0, result.output
        tarballs = list(out.glob("*.tar.gz"))
        assert len(tarballs) == 1
        assert tarballs[0].name == "train-1.0.0.tar.gz"

    def test_publish_no_args_no_project(self, tmp_path: Path) -> None:
        """Clean error when no .agent/ exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["publish", "-o", str(tmp_path), "--path", str(tmp_path)])
        assert result.exit_code != 0

    def test_publish_round_trip_with_install(self, tmp_path: Path) -> None:
        """Publish from one project, install into another."""
        # Publish from ml-pipeline
        src_project = tmp_path / "src"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", src_project)
        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        runner.invoke(cli, [
            "publish", "-o", str(out), "--path", str(src_project), "--skill", "train",
        ])
        tarball = out / "train-1.0.0.tar.gz"
        assert tarball.exists()

        # Install into a fresh project
        dest_project = tmp_path / "dest"
        dest_project.mkdir()
        runner.invoke(cli, [
            "init", "--name", "dest-proj", "--language", "python", "--path", str(dest_project),
        ])
        result = runner.invoke(cli, [
            "install", str(tarball), "--path", str(dest_project),
        ])
        assert result.exit_code == 0, result.output

        # Validate the destination project
        result = runner.invoke(cli, ["validate", str(dest_project)])
        assert result.exit_code == 0, result.output


class TestPublishTemplate:
    """Publish entire .agent/ directory as a template."""

    def test_publish_template_creates_tarball(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", project)
        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, [
            "publish", "--template", "-o", str(out), "--path", str(project),
        ])
        assert result.exit_code == 0, result.output
        assert "Published template" in result.output

        tarballs = list(out.glob("*.tar.gz"))
        assert len(tarballs) == 1
        assert "ml-model-factory" in tarballs[0].name

    def test_template_excludes_memory_by_default(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", project)
        # Ensure memory file exists
        memory_dir = project / ".agent" / "memory"
        memory_dir.mkdir(exist_ok=True)
        (memory_dir / "project.md").write_text("# Memory\n")

        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        runner.invoke(cli, [
            "publish", "--template", "-o", str(out), "--path", str(project),
        ])

        tarball = list(out.glob("*.tar.gz"))[0]
        members = _tarball_members(tarball)
        # memory/ files should NOT be in the tarball
        assert not any("memory/" in m for m in members)

    def test_template_excludes_local_yaml_by_default(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", project)
        (project / ".agent" / "local.yaml").write_text("env:\n  SECRET: x\n")

        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        runner.invoke(cli, [
            "publish", "--template", "-o", str(out), "--path", str(project),
        ])

        tarball = list(out.glob("*.tar.gz"))[0]
        members = _tarball_members(tarball)
        assert not any("local.yaml" in m for m in members)

    def test_template_include_memory(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", project)
        memory_dir = project / ".agent" / "memory"
        memory_dir.mkdir(exist_ok=True)
        (memory_dir / "project.md").write_text("# Memory\n")

        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        runner.invoke(cli, [
            "publish", "--template", "--include-memory",
            "-o", str(out), "--path", str(project),
        ])

        tarball = list(out.glob("*.tar.gz"))[0]
        members = _tarball_members(tarball)
        assert any("memory/" in m for m in members)

    def test_template_include_all(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", project)
        (project / ".agent" / "local.yaml").write_text("env:\n  KEY: val\n")
        memory_dir = project / ".agent" / "memory"
        memory_dir.mkdir(exist_ok=True)
        (memory_dir / "project.md").write_text("# Memory\n")

        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        runner.invoke(cli, [
            "publish", "--template", "--include-all",
            "-o", str(out), "--path", str(project),
        ])

        tarball = list(out.glob("*.tar.gz"))[0]
        members = _tarball_members(tarball)
        assert any("local.yaml" in m for m in members)
        assert any("memory/" in m for m in members)

    def test_template_contains_agent_dir_structure(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", project)
        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        runner.invoke(cli, [
            "publish", "--template", "-o", str(out), "--path", str(project),
        ])

        tarball = list(out.glob("*.tar.gz"))[0]
        members = _tarball_members(tarball)
        # Should have {name}/.agent/ structure
        assert any(".agent/agent.yaml" in m for m in members)
        assert any(".agent/instructions.md" in m for m in members)
        assert any(".agent/skills/" in m for m in members)

    def test_template_validates_before_publish(self, tmp_path: Path) -> None:
        """Publish should fail if .agent/ doesn't exist."""
        project = tmp_path / "project"
        project.mkdir()
        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, [
            "publish", "--template", "-o", str(out), "--path", str(project),
        ])
        assert result.exit_code != 0

    def test_template_custom_excludes(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", project)
        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        runner.invoke(cli, [
            "publish", "--template",
            "--exclude", "registry/**",
            "-o", str(out), "--path", str(project),
        ])

        tarball = list(out.glob("*.tar.gz"))[0]
        members = _tarball_members(tarball)
        assert not any("registry/" in m for m in members)


class TestPublishTemplateRoundTrip:
    """Publish a template, then install via init --from."""

    def test_round_trip_with_local_tarball(self, tmp_path: Path) -> None:
        # Publish template
        src = tmp_path / "src"
        shutil.copytree(EXAMPLES_DIR / "ml-pipeline", src)
        out = tmp_path / "out"
        out.mkdir()

        runner = CliRunner()
        runner.invoke(cli, [
            "publish", "--template", "-o", str(out), "--path", str(src),
        ])
        tarball = list(out.glob("*.tar.gz"))[0]

        # Init from tarball
        dest = tmp_path / "dest"
        dest.mkdir()
        result = runner.invoke(cli, [
            "init", "--from", str(tarball), "--path", str(dest),
        ])
        assert result.exit_code == 0, result.output
        assert (dest / ".agent" / "agent.yaml").exists()
        assert (dest / ".agent" / "instructions.md").exists()
        assert (dest / ".agent" / "skills").exists()

        # Validate the result
        result = runner.invoke(cli, ["validate", str(dest)])
        assert result.exit_code == 0, result.output
