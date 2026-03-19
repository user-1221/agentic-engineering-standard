"""Tests for lifecycle.yaml schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aes.validator import validate_file, validate_agent_dir


@pytest.fixture
def tmp_lifecycle(tmp_path):
    """Create a temporary lifecycle.yaml file."""
    def _write(data):
        p = tmp_path / "lifecycle.yaml"
        p.write_text(yaml.dump(data, default_flow_style=False))
        return p
    return _write


class TestLifecycleSchema:
    def test_valid_minimal(self, tmp_lifecycle):
        result = validate_file(
            tmp_lifecycle({
                "apiVersion": "aes/v1",
                "kind": "Lifecycle",
                "hooks": {},
            }),
            "lifecycle",
        )
        assert result.valid, result.errors

    def test_valid_full(self, tmp_lifecycle):
        result = validate_file(
            tmp_lifecycle({
                "apiVersion": "aes/v1",
                "kind": "Lifecycle",
                "profile": "standard",
                "disabled_hooks": ["audit-log"],
                "hooks": {
                    "on_session_start": [{
                        "name": "restore-context",
                        "action": "script",
                        "command": "node scripts/restore.js",
                        "profile": "minimal",
                        "timeout_seconds": 10,
                        "async": False,
                        "fail_strategy": "warn",
                    }],
                    "on_session_end": [{
                        "name": "persist-summary",
                        "action": "script",
                        "command": "node scripts/persist.js",
                        "async": True,
                        "fail_strategy": "skip",
                    }],
                    "pre_tool_use": [{
                        "name": "quality-gate",
                        "action": "script",
                        "command": "node scripts/gate.js",
                        "profile": "strict",
                        "filter": {"tools": ["Edit", "Write"]},
                        "fail_strategy": "abort",
                    }],
                    "post_tool_use": [{
                        "name": "audit-log",
                        "action": "script",
                        "command": "node scripts/audit.js",
                        "async": True,
                        "output": {"file": "logs/audit.jsonl", "format": "jsonl"},
                    }],
                    "heartbeat": {
                        "interval_minutes": 30,
                        "actions": [{
                            "name": "check-tasks",
                            "action": "checklist",
                            "checklist_file": "heartbeat.md",
                        }],
                    },
                    "on_error": [{
                        "name": "error-recovery",
                        "action": "script",
                        "command": "node scripts/recover.js",
                        "max_retries": 3,
                        "backoff_seconds": 5,
                    }],
                },
            }),
            "lifecycle",
        )
        assert result.valid, result.errors

    def test_invalid_profile(self, tmp_lifecycle):
        result = validate_file(
            tmp_lifecycle({
                "apiVersion": "aes/v1",
                "kind": "Lifecycle",
                "profile": "ultra",
                "hooks": {},
            }),
            "lifecycle",
        )
        assert not result.valid

    def test_invalid_fail_strategy(self, tmp_lifecycle):
        result = validate_file(
            tmp_lifecycle({
                "apiVersion": "aes/v1",
                "kind": "Lifecycle",
                "hooks": {
                    "on_session_start": [{
                        "name": "bad-hook",
                        "action": "script",
                        "command": "echo hi",
                        "fail_strategy": "explode",
                    }],
                },
            }),
            "lifecycle",
        )
        assert not result.valid

    def test_invalid_action_type(self, tmp_lifecycle):
        result = validate_file(
            tmp_lifecycle({
                "apiVersion": "aes/v1",
                "kind": "Lifecycle",
                "hooks": {
                    "on_session_start": [{
                        "name": "bad",
                        "action": "execute",
                    }],
                },
            }),
            "lifecycle",
        )
        assert not result.valid

    def test_wrong_kind_rejected(self, tmp_lifecycle):
        result = validate_file(
            tmp_lifecycle({
                "apiVersion": "aes/v1",
                "kind": "WrongKind",
                "hooks": {},
            }),
            "lifecycle",
        )
        assert not result.valid

    def test_missing_hooks_rejected(self, tmp_lifecycle):
        result = validate_file(
            tmp_lifecycle({
                "apiVersion": "aes/v1",
                "kind": "Lifecycle",
            }),
            "lifecycle",
        )
        assert not result.valid

    def test_unknown_event_rejected(self, tmp_lifecycle):
        result = validate_file(
            tmp_lifecycle({
                "apiVersion": "aes/v1",
                "kind": "Lifecycle",
                "hooks": {
                    "on_deploy": [{"name": "x", "action": "script", "command": "y"}],
                },
            }),
            "lifecycle",
        )
        assert not result.valid


class TestLifecycleInAgentDir:
    def test_lifecycle_validated_in_agent_dir(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text(yaml.dump({
            "aes": "1.4",
            "name": "test-project",
            "version": "0.1.0",
            "description": "Test project",
            "agent": {"instructions": "instructions.md"},
        }))
        (agent_dir / "instructions.md").write_text("# Test")
        (agent_dir / "lifecycle.yaml").write_text(yaml.dump({
            "apiVersion": "aes/v1",
            "kind": "Lifecycle",
            "hooks": {
                "on_session_start": [{
                    "name": "restore",
                    "action": "script",
                    "command": "node scripts/restore.js",
                }],
            },
        }))
        results = validate_agent_dir(agent_dir)
        lifecycle_results = [r for r in results if r.schema_type == "lifecycle"]
        assert len(lifecycle_results) >= 1
        # Schema validation should pass
        schema_result = lifecycle_results[0]
        assert schema_result.valid, schema_result.errors

    def test_lifecycle_script_warning(self, tmp_path):
        """Warn when lifecycle references scripts that don't exist."""
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text(yaml.dump({
            "aes": "1.4",
            "name": "test-project",
            "version": "0.1.0",
            "description": "Test project",
            "agent": {"instructions": "instructions.md"},
        }))
        (agent_dir / "instructions.md").write_text("# Test")
        (agent_dir / "lifecycle.yaml").write_text(yaml.dump({
            "apiVersion": "aes/v1",
            "kind": "Lifecycle",
            "hooks": {
                "on_session_start": [{
                    "name": "restore",
                    "action": "script",
                    "command": "node .agent/scripts/nonexistent.js",
                }],
            },
        }))
        results = validate_agent_dir(agent_dir)
        warnings = [
            r for r in results
            if r.schema_type == "lifecycle" and r.valid and r.errors
        ]
        assert any("nonexistent.js" in str(w.errors) for w in warnings)
