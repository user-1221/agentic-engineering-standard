"""Tests for AES MCP server tools."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

mcp = pytest.importorskip("mcp")

from aes.mcp_server import aes_inspect, aes_search, aes_validate, aes_install


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_INDEX = {
    "packages": {
        "deploy": {
            "description": "Deploy the app",
            "latest": "1.1.0",
            "type": "skill",
            "tags": ["devops", "deployment"],
            "versions": {
                "1.0.0": {
                    "url": "packages/deploy/1.0.0.tar.gz",
                    "sha256": "aaa",
                    "published_at": "2025-01-01T00:00:00Z",
                },
                "1.1.0": {
                    "url": "packages/deploy/1.1.0.tar.gz",
                    "sha256": "bbb",
                    "published_at": "2025-06-01T00:00:00Z",
                },
            },
        },
        "train": {
            "description": "Train ML models",
            "latest": "2.0.0",
            "type": "skill",
            "tags": ["ml", "training"],
            "versions": {
                "2.0.0": {
                    "url": "packages/train/2.0.0.tar.gz",
                    "sha256": "ccc",
                    "published_at": "2025-03-01T00:00:00Z",
                },
            },
        },
        "ml-starter": {
            "description": "ML project template",
            "latest": "1.0.0",
            "type": "template",
            "tags": ["ml"],
            "versions": {
                "1.0.0": {
                    "url": "packages/ml-starter/1.0.0.tar.gz",
                    "sha256": "ddd",
                    "published_at": "2025-02-01T00:00:00Z",
                },
            },
        },
    }
}


def _mock_fetch_index(*args, **kwargs):
    return MOCK_INDEX


# ---------------------------------------------------------------------------
# aes_search
# ---------------------------------------------------------------------------


class TestAesSearch:
    @patch("aes.mcp_server.search_packages", wraps=None)
    @patch("aes.mcp_server.fetch_index", side_effect=_mock_fetch_index)
    def test_search_all(self, _fi, _sp):
        """Empty query via search_packages returns all packages."""
        # Call the real search_packages with our mock index
        from aes.registry import search_packages as real_search

        with patch("aes.mcp_server.search_packages", side_effect=lambda **kw: real_search(index=MOCK_INDEX, **kw)):
            result = json.loads(aes_search())
        assert len(result) == 3

    @patch("aes.mcp_server.search_packages")
    def test_search_keyword(self, mock_search):
        mock_search.return_value = [
            {"name": "deploy", "description": "Deploy the app", "latest": "1.1.0", "type": "skill", "tags": ["devops"]}
        ]
        result = json.loads(aes_search(query="deploy"))
        assert len(result) == 1
        assert result[0]["name"] == "deploy"

    @patch("aes.mcp_server.search_packages")
    def test_search_tag(self, mock_search):
        mock_search.return_value = [
            {"name": "train", "description": "Train ML models", "latest": "2.0.0", "type": "skill", "tags": ["ml"]}
        ]
        result = json.loads(aes_search(tag="ml"))
        mock_search.assert_called_once_with(query="", tag="ml", domain=None, pkg_type=None)
        assert result[0]["name"] == "train"

    @patch("aes.mcp_server.search_packages")
    def test_search_type(self, mock_search):
        mock_search.return_value = [
            {"name": "ml-starter", "type": "template", "latest": "1.0.0", "description": "ML project template", "tags": ["ml"]}
        ]
        result = json.loads(aes_search(pkg_type="template"))
        mock_search.assert_called_once_with(query="", tag=None, domain=None, pkg_type="template")
        assert result[0]["type"] == "template"

    @patch("aes.mcp_server.search_packages")
    def test_search_no_results(self, mock_search):
        mock_search.return_value = []
        result = json.loads(aes_search(query="nonexistent"))
        assert result == []

    @patch("aes.mcp_server.search_packages", side_effect=Exception("Connection refused"))
    def test_search_network_error(self, _mock):
        result = json.loads(aes_search())
        assert "error" in result
        assert "Connection refused" in result["error"]


# ---------------------------------------------------------------------------
# aes_inspect
# ---------------------------------------------------------------------------


class TestAesInspect:
    @patch("aes.mcp_server.fetch_index", side_effect=_mock_fetch_index)
    def test_inspect_existing(self, _mock):
        result = json.loads(aes_inspect(name="deploy"))
        assert result["name"] == "deploy"
        assert result["type"] == "skill"
        assert result["latest"] == "1.1.0"
        assert "1.0.0" in result["versions"]
        assert "1.1.0" in result["versions"]
        assert result["tags"] == ["devops", "deployment"]

    @patch("aes.mcp_server.fetch_index", side_effect=_mock_fetch_index)
    def test_inspect_nonexistent(self, _mock):
        result = json.loads(aes_inspect(name="does-not-exist"))
        assert "error" in result
        assert "not found" in result["error"]

    @patch("aes.mcp_server.fetch_index", side_effect=Exception("timeout"))
    def test_inspect_network_error(self, _mock):
        result = json.loads(aes_inspect(name="deploy"))
        assert "error" in result
        assert "timeout" in result["error"]


# ---------------------------------------------------------------------------
# aes_validate
# ---------------------------------------------------------------------------


class TestAesValidate:
    def test_validate_valid_project(self):
        """Validate the ml-pipeline example — should pass."""
        examples_dir = Path(__file__).resolve().parent.parent.parent / "examples" / "ml-pipeline"
        if not (examples_dir / ".agent").exists():
            pytest.skip("examples/ml-pipeline not available")
        result = json.loads(aes_validate(project_path=str(examples_dir)))
        assert result["summary"]["failed"] == 0
        assert result["summary"]["passed"] > 0

    def test_validate_missing_agent_dir(self, tmp_path):
        result = json.loads(aes_validate(project_path=str(tmp_path)))
        assert "error" in result
        assert ".agent" in result["error"]


# ---------------------------------------------------------------------------
# aes_install
# ---------------------------------------------------------------------------


class TestAesInstall:
    def test_install_missing_agent_dir(self, tmp_path):
        result = json.loads(aes_install(source="aes-hub/deploy@^1.0", project_path=str(tmp_path)))
        assert "error" in result
        assert ".agent" in result["error"]

    def test_install_unknown_source(self, tmp_path):
        (tmp_path / ".agent").mkdir()
        result = json.loads(aes_install(source="???bad???", project_path=str(tmp_path)))
        assert "error" in result

    def test_install_git_unsupported(self, tmp_path):
        (tmp_path / ".agent").mkdir()
        result = json.loads(aes_install(source="github:user/repo", project_path=str(tmp_path)))
        assert "error" in result
        assert "not yet supported" in result["error"]

    def test_install_local_skill(self, tmp_path):
        """Install a skill from a local directory."""
        # Set up a minimal project with .agent/
        project = tmp_path / "project"
        project.mkdir()
        agent_dir = project / ".agent"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text(
            "aes: '1.0'\nname: test\nversion: 1.0.0\ndescription: test\nskills: []\n"
        )
        (agent_dir / "skills").mkdir()
        (agent_dir / "skills" / "vendor").mkdir()

        # Set up a skill source directory
        skill_src = tmp_path / "my-skill"
        skill_src.mkdir()
        (skill_src / "deploy.skill.yaml").write_text(
            "aes_skill: '1.0'\nid: deploy\nname: Deploy\nversion: 1.0.0\ndescription: Deploy\n"
        )
        (skill_src / "deploy.md").write_text("# Deploy\nDeploy the app.\n")

        result = json.loads(aes_install(source=str(skill_src), project_path=str(project)))
        assert result.get("installed") == "deploy"
        assert (agent_dir / "skills" / "vendor" / "deploy" / "deploy.skill.yaml").exists()
