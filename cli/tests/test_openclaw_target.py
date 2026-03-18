"""Tests for the OpenClaw sync target."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import click
import pytest
import yaml

from aes.targets._base import AgentContext
from aes.targets.openclaw import OpenClawTarget


EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"


def _make_ctx(
    tmp_path: Path,
    manifest: dict,
    permissions: dict | None = None,
    skill_runbooks: dict | None = None,
    skill_metadata: dict | None = None,
) -> AgentContext:
    """Build a minimal AgentContext for testing."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(exist_ok=True)
    return AgentContext(
        project_root=tmp_path,
        agent_dir=agent_dir,
        manifest=manifest,
        instructions="Test instructions.",
        orchestrator=None,
        skill_runbooks=skill_runbooks or {},
        permissions=permissions,
        commands=[],
        memory_project=None,
        skill_metadata=skill_metadata or {},
    )


def _base_manifest() -> dict:
    """Return a manifest with the minimum required sections for openclaw."""
    return {
        "name": "test-agent",
        "version": "1.0.0",
        "description": "A test agent",
        "identity": {
            "persona": "You are helpful.",
            "name": "TestBot",
            "emoji": "\U0001F916",
        },
        "model": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    }


# ---------------------------------------------------------------------------
# Sync-time enforcement tests
# ---------------------------------------------------------------------------

class TestSyncTimeEnforcement:

    def test_errors_without_identity(self, tmp_path: Path) -> None:
        manifest = _base_manifest()
        del manifest["identity"]
        ctx = _make_ctx(tmp_path, manifest)
        target = OpenClawTarget()
        with pytest.raises(click.ClickException, match="identity"):
            target.plan(ctx, force=False)

    def test_errors_without_model(self, tmp_path: Path) -> None:
        manifest = _base_manifest()
        del manifest["model"]
        ctx = _make_ctx(tmp_path, manifest)
        target = OpenClawTarget()
        with pytest.raises(click.ClickException, match="model"):
            target.plan(ctx, force=False)

    def test_warns_without_channels(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path, _base_manifest())
        target = OpenClawTarget()
        plan = target.plan(ctx, force=False)
        assert any("channels" in w for w in plan.warnings)


# ---------------------------------------------------------------------------
# Happy-path generation tests
# ---------------------------------------------------------------------------

class TestOpenClawGeneration:

    def test_generates_openclaw_json(self, tmp_path: Path) -> None:
        manifest = _base_manifest()
        manifest["channels"] = {
            "telegram": {"enabled": True, "bot_token_env": "TG_TOKEN"},
        }
        ctx = _make_ctx(tmp_path, manifest)
        target = OpenClawTarget()
        plan = target.plan(ctx, force=False)

        oc_file = next(
            f for f in plan.files
            if f.relative_path == ".openclaw/openclaw.json"
        )
        config = json.loads(oc_file.content)
        assert config["llm"]["provider"] == "anthropic"
        assert config["llm"]["apiKey"] == "${ANTHROPIC_API_KEY}"
        assert config["integrations"]["telegram"]["botToken"] == "${TG_TOKEN}"
        assert config["_aes_sync"] is True

    def test_generates_workspace_markdown_files(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path, _base_manifest())
        target = OpenClawTarget()
        plan = target.plan(ctx, force=False)
        paths = {f.relative_path for f in plan.files}
        assert ".openclaw/workspace/SOUL.md" in paths
        assert ".openclaw/workspace/IDENTITY.md" in paths
        assert ".openclaw/workspace/AGENTS.md" in paths
        assert ".openclaw/workspace/MEMORY.md" in paths
        assert ".openclaw/workspace/HEARTBEAT.md" in paths
        assert ".openclaw/workspace/TOOLS.md" in paths

    def test_generates_skill_md(self, tmp_path: Path) -> None:
        manifest = _base_manifest()
        skill_runbooks = {"greeting": "## Purpose\nGreet the user.\n"}
        skill_metadata = {
            "greeting": {
                "name": "Greeting",
                "description": "Greet users",
                "emoji": "\U0001F44B",
                "requires_env": ["GREET_KEY"],
                "primary_env": "GREET_KEY",
                "version": "1.0.0",
                "activation": "auto",
                "negative_triggers": [],
                "allowed_tools": None,
            },
        }
        ctx = _make_ctx(tmp_path, manifest,
                        skill_runbooks=skill_runbooks,
                        skill_metadata=skill_metadata)
        target = OpenClawTarget()
        plan = target.plan(ctx, force=False)

        skill_file = next(
            f for f in plan.files
            if "skills/greeting/SKILL.md" in f.relative_path
        )
        assert "name: Greeting" in skill_file.content
        assert "openclaw" in skill_file.content
        assert "primaryEnv" in skill_file.content

    def test_generates_policy_yaml(self, tmp_path: Path) -> None:
        manifest = _base_manifest()
        manifest["sandbox"] = {"enabled": True, "runtime": "openshell"}
        permissions = {
            "filesystem": {
                "enforcement": "enforce",
                "read_only": ["/usr"],
                "read_write": ["/sandbox"],
            },
        }
        ctx = _make_ctx(tmp_path, manifest, permissions=permissions)
        target = OpenClawTarget()
        plan = target.plan(ctx, force=False)

        policy_file = next(
            f for f in plan.files
            if f.relative_path == ".openclaw/policy.yaml"
        )
        assert "filesystem_policy" in policy_file.content
        assert "process_policy" in policy_file.content

    def test_skips_policy_without_openshell(self, tmp_path: Path) -> None:
        manifest = _base_manifest()
        manifest["sandbox"] = {"enabled": True, "runtime": "docker"}
        ctx = _make_ctx(tmp_path, manifest)
        target = OpenClawTarget()
        plan = target.plan(ctx, force=False)
        paths = {f.relative_path for f in plan.files}
        assert ".openclaw/policy.yaml" not in paths

    def test_no_hardcoded_secrets(self, tmp_path: Path) -> None:
        manifest = _base_manifest()
        manifest["channels"] = {
            "telegram": {"enabled": True, "bot_token_env": "TG_TOKEN"},
        }
        ctx = _make_ctx(tmp_path, manifest)
        target = OpenClawTarget()
        plan = target.plan(ctx, force=False)

        oc_file = next(
            f for f in plan.files
            if f.relative_path == ".openclaw/openclaw.json"
        )
        content = oc_file.content
        # Must use ${VAR} syntax, never raw values
        assert "${ANTHROPIC_API_KEY}" in content
        assert "${TG_TOKEN}" in content
        # Must NOT contain actual key patterns
        assert "sk-ant-" not in content
        assert "ghp_" not in content

    def test_multi_agent_workspaces(self, tmp_path: Path) -> None:
        manifest = _base_manifest()
        manifest["agents"] = [
            {"id": "main", "workspace": "workspace"},
            {"id": "researcher", "workspace": "workspace-studio"},
        ]
        ctx = _make_ctx(tmp_path, manifest)
        target = OpenClawTarget()
        plan = target.plan(ctx, force=False)
        paths = {f.relative_path for f in plan.files}
        assert any("workspace-studio" in p for p in paths)

    def test_sentinel_in_generated_files(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path, _base_manifest())
        target = OpenClawTarget()
        plan = target.plan(ctx, force=False)

        for f in plan.files:
            if f.relative_path.endswith(".json"):
                assert "_aes_sync" in f.content
            elif f.relative_path.endswith(".md"):
                assert "Generated by" in f.content


# ---------------------------------------------------------------------------
# Integration test with real example
# ---------------------------------------------------------------------------

class TestPersonalAssistantExample:

    def test_sync_personal_assistant(self, tmp_path: Path) -> None:
        """Sync the personal-assistant example with openclaw target."""
        src = EXAMPLES_DIR / "personal-assistant"
        if not src.exists():
            pytest.skip("personal-assistant example not found")
        dst = tmp_path / "pa"
        shutil.copytree(src, dst)

        from click.testing import CliRunner
        from aes.__main__ import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["sync", str(dst), "-t", "openclaw"])
        assert result.exit_code == 0

        oc_json = dst / ".openclaw" / "openclaw.json"
        assert oc_json.exists()
        config = json.loads(oc_json.read_text())
        assert config["llm"]["provider"] == "anthropic"

        skill_md = dst / ".openclaw" / "workspace" / "skills" / "web-search" / "SKILL.md"
        assert skill_md.exists()
        assert "primaryEnv" in skill_md.read_text()
