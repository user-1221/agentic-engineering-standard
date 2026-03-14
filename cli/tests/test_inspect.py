"""Tests for aes inspect command."""

from __future__ import annotations

import os
import shutil
import tarfile
from pathlib import Path
from unittest.mock import patch

import yaml
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


# ---------------------------------------------------------------------------
# Remote registry inspect tests
# ---------------------------------------------------------------------------

MOCK_INDEX = {
    "packages": {
        "deploy": {
            "description": "Blue-green deploy skill",
            "latest": "1.1.0",
            "type": "skill",
            "visibility": "public",
            "tags": ["devops", "deployment"],
            "versions": {
                "1.0.0": {
                    "url": "packages/deploy/1.0.0.tar.gz",
                    "sha256": "aaa",
                    "published_at": "2025-01-01T10:00:00Z",
                },
                "1.1.0": {
                    "url": "packages/deploy/1.1.0.tar.gz",
                    "sha256": "bbb",
                    "published_at": "2025-06-01T12:00:00Z",
                },
            },
        },
        "ml-starter": {
            "description": "ML project template",
            "latest": "1.0.0",
            "type": "template",
            "visibility": "public",
            "tags": ["ml"],
            "versions": {
                "1.0.0": {
                    "url": "packages/ml-starter/1.0.0.tar.gz",
                    "sha256": "ccc",
                    "published_at": "2025-03-01T00:00:00Z",
                },
            },
        },
    }
}


def _make_skill_tarball(tmp_path: Path, skill_id: str = "deploy", version: str = "1.1.0") -> Path:
    """Create a minimal skill tarball and return its path."""
    skill_dir = tmp_path / "build" / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "aes_skill": "1.0",
        "id": skill_id,
        "name": "Deploy Service",
        "version": version,
        "description": "Blue-green deploy",
        "inputs": {
            "required": [{"name": "service", "type": "string", "description": "Service to deploy"}],
            "optional": [{"name": "region", "type": "string", "description": "Target region"}],
        },
        "outputs": [{"name": "deploy_id", "type": "string", "description": "Deployment ID"}],
        "depends_on": ["provision"],
        "blocks": ["rollback"],
        "triggers": [{"type": "manual", "command": "deploy.sh"}],
        "negative_triggers": ["Do NOT use for database migrations"],
        "tags": ["devops"],
    }
    (skill_dir / f"{skill_id}.skill.yaml").write_text(yaml.dump(manifest))
    (skill_dir / f"{skill_id}.md").write_text(f"# {skill_id}\nRunbook content.\n")

    tarball = tmp_path / "build" / f"{skill_id}-{version}.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        tar.add(skill_dir, arcname=skill_id)
    return tarball


def _make_template_tarball(tmp_path: Path, name: str = "ml-starter", version: str = "1.0.0") -> Path:
    """Create a minimal template tarball with .agent/ directory."""
    agent_dir = tmp_path / "build" / name / ".agent"
    agent_dir.mkdir(parents=True, exist_ok=True)

    agent_yaml = {
        "aes": "1.0",
        "name": name,
        "version": version,
        "description": "ML project template",
        "domain": "ml",
        "runtime": {"language": "python", "version": "3.10"},
        "skills": [
            {"id": "train", "manifest": "skills/train.skill.yaml", "runbook": "skills/train.md"},
        ],
    }
    (agent_dir / "agent.yaml").write_text(yaml.dump(agent_yaml))

    skills_dir = agent_dir / "skills"
    skills_dir.mkdir()
    (skills_dir / "train.skill.yaml").write_text(yaml.dump({
        "aes_skill": "1.0", "id": "train", "name": "Train", "version": "1.0.0",
        "description": "Train models",
    }))
    (skills_dir / "train.md").write_text("# Train\nTrain models.\n")

    tarball = tmp_path / "build" / f"{name}-{version}.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        tar.add(tmp_path / "build" / name, arcname=name)
    return tarball


def _mock_download_skill(tarball_src: Path):
    """Return a mock download_package that copies a pre-built tarball."""
    def _download(name, version, sha256, dest, registry_url=None):
        dst = dest / f"{name}-{version}.tar.gz"
        shutil.copy2(tarball_src, dst)
        return dst
    return _download


class TestRemoteInspect:

    def test_inspect_remote_skill(self, tmp_path):
        tarball = _make_skill_tarball(tmp_path)
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX), \
             patch("aes.commands.inspect.download_package", side_effect=_mock_download_skill(tarball)):
            result = runner.invoke(cli, ["inspect", "deploy"])
        assert result.exit_code == 0, result.output
        # Registry metadata
        assert "deploy" in result.output
        assert "registry" in result.output
        assert "Blue-green deploy skill" in result.output
        # Skill details
        assert "Skill Details" in result.output
        assert "Deploy Service" in result.output
        assert "service" in result.output  # input name
        assert "deploy_id" in result.output  # output name

    def test_inspect_remote_shows_versions_table(self, tmp_path):
        tarball = _make_skill_tarball(tmp_path)
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX), \
             patch("aes.commands.inspect.download_package", side_effect=_mock_download_skill(tarball)):
            result = runner.invoke(cli, ["inspect", "deploy"])
        assert result.exit_code == 0, result.output
        assert "Versions" in result.output
        assert "1.0.0" in result.output
        assert "1.1.0" in result.output
        assert "latest" in result.output

    def test_inspect_remote_shows_inputs_outputs(self, tmp_path):
        tarball = _make_skill_tarball(tmp_path)
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX), \
             patch("aes.commands.inspect.download_package", side_effect=_mock_download_skill(tarball)):
            result = runner.invoke(cli, ["inspect", "deploy"])
        assert result.exit_code == 0, result.output
        assert "Inputs" in result.output
        assert "Outputs" in result.output
        assert "service" in result.output
        assert "region" in result.output
        assert "deploy_id" in result.output

    def test_inspect_remote_shows_dependencies(self, tmp_path):
        tarball = _make_skill_tarball(tmp_path)
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX), \
             patch("aes.commands.inspect.download_package", side_effect=_mock_download_skill(tarball)):
            result = runner.invoke(cli, ["inspect", "deploy"])
        assert result.exit_code == 0, result.output
        assert "Dependencies" in result.output
        assert "provision" in result.output
        assert "rollback" in result.output

    def test_inspect_remote_shows_triggers(self, tmp_path):
        tarball = _make_skill_tarball(tmp_path)
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX), \
             patch("aes.commands.inspect.download_package", side_effect=_mock_download_skill(tarball)):
            result = runner.invoke(cli, ["inspect", "deploy"])
        assert result.exit_code == 0, result.output
        assert "Triggers" in result.output
        assert "deploy.sh" in result.output
        assert "Negative Triggers" in result.output
        assert "database migrations" in result.output

    def test_inspect_remote_not_found(self):
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX):
            result = runner.invoke(cli, ["inspect", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_inspect_remote_specific_version(self, tmp_path):
        tarball = _make_skill_tarball(tmp_path, version="1.0.0")
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX), \
             patch("aes.commands.inspect.download_package", side_effect=_mock_download_skill(tarball)):
            result = runner.invoke(cli, ["inspect", "deploy@1.0.0"])
        assert result.exit_code == 0, result.output
        assert "v1.0.0" in result.output

    def test_inspect_remote_with_prefix(self, tmp_path):
        tarball = _make_skill_tarball(tmp_path)
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX), \
             patch("aes.commands.inspect.download_package", side_effect=_mock_download_skill(tarball)):
            result = runner.invoke(cli, ["inspect", "aes-hub/deploy"])
        assert result.exit_code == 0, result.output
        assert "deploy" in result.output
        assert "Skill Details" in result.output

    def test_inspect_remote_fetch_failure(self):
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", side_effect=Exception("Network error")):
            result = runner.invoke(cli, ["inspect", "deploy"])
        assert result.exit_code == 1
        assert "Failed to fetch" in result.output

    def test_inspect_remote_download_failure_shows_metadata_only(self):
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX), \
             patch("aes.commands.inspect.download_package", side_effect=Exception("Download failed")):
            result = runner.invoke(cli, ["inspect", "deploy"])
        assert result.exit_code == 0, result.output
        # Should still show registry metadata
        assert "deploy" in result.output
        assert "Versions" in result.output
        # But not skill details
        assert "Skill Details" not in result.output
        assert "metadata only" in result.output

    def test_inspect_remote_template(self, tmp_path):
        tarball = _make_template_tarball(tmp_path)
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX), \
             patch("aes.commands.inspect.download_package", side_effect=_mock_download_skill(tarball)):
            result = runner.invoke(cli, ["inspect", "ml-starter"])
        assert result.exit_code == 0, result.output
        # Registry metadata
        assert "ml-starter" in result.output
        assert "template" in result.output
        # Template inspection (reuses local inspect)
        assert "train" in result.output
        assert "Summary" in result.output

    def test_inspect_remote_version_no_match(self):
        runner = CliRunner()
        with patch("aes.commands.inspect.fetch_index", return_value=MOCK_INDEX):
            result = runner.invoke(cli, ["inspect", "deploy@9.9.9"])
        assert result.exit_code == 1
        assert "No version" in result.output
