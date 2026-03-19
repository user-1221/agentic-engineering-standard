"""Tests for rules config schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aes.validator import validate_file, validate_agent_dir


@pytest.fixture
def tmp_yaml(tmp_path):
    """Write arbitrary YAML data to a temp file."""
    def _write(name, data):
        p = tmp_path / name
        p.write_text(yaml.dump(data, default_flow_style=False))
        return p
    return _write


class TestRulesConfigSchema:
    def test_valid_full_config(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("rules.yaml", {
                "apiVersion": "aes/v1",
                "kind": "RulesConfig",
                "languages": ["typescript", "python"],
                "detection": {
                    "typescript": ["*.ts", "*.tsx", "tsconfig.json"],
                    "python": ["*.py", "pyproject.toml"],
                },
                "loading": {
                    "always": ["common"],
                },
                "overrides": {
                    "testing": {
                        "min_coverage": 90,
                    },
                    "coding-style": {
                        "max_line_length": 120,
                    },
                },
            }),
            "rules-config",
        )
        assert result.valid, result.errors

    def test_minimal_config(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("rules.yaml", {
                "apiVersion": "aes/v1",
                "kind": "RulesConfig",
            }),
            "rules-config",
        )
        assert result.valid, result.errors

    def test_wrong_kind_rejected(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("rules.yaml", {
                "apiVersion": "aes/v1",
                "kind": "WrongKind",
            }),
            "rules-config",
        )
        assert not result.valid

    def test_languages_must_be_array(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("rules.yaml", {
                "apiVersion": "aes/v1",
                "kind": "RulesConfig",
                "languages": "python",
            }),
            "rules-config",
        )
        assert not result.valid

    def test_additional_properties_rejected(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("rules.yaml", {
                "apiVersion": "aes/v1",
                "kind": "RulesConfig",
                "unknown_field": True,
            }),
            "rules-config",
        )
        assert not result.valid


class TestRulesInAgentDir:
    def test_rules_validated_in_agent_dir(self, tmp_path):
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

        rules_dir = agent_dir / "rules"
        rules_dir.mkdir()
        # Create the python/ dir so no warning is triggered
        (rules_dir / "python").mkdir()
        (rules_dir / "rules.yaml").write_text(yaml.dump({
            "apiVersion": "aes/v1",
            "kind": "RulesConfig",
            "languages": ["python"],
        }))

        results = validate_agent_dir(agent_dir)
        rules_results = [r for r in results if r.schema_type == "rules-config"]
        assert len(rules_results) == 1
        assert rules_results[0].valid

    def test_missing_language_dir_warns(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text(yaml.dump({
            "aes": "1.4",
            "name": "test",
            "version": "0.1.0",
            "description": "Test",
            "agent": {"instructions": "instructions.md"},
        }))
        (agent_dir / "instructions.md").write_text("# Test")

        rules_dir = agent_dir / "rules"
        rules_dir.mkdir()
        (rules_dir / "rules.yaml").write_text(yaml.dump({
            "apiVersion": "aes/v1",
            "kind": "RulesConfig",
            "languages": ["rust"],
        }))

        results = validate_agent_dir(agent_dir)
        warnings = [
            r for r in results
            if r.schema_type == "rules-config" and r.valid and r.errors
        ]
        assert any("rust" in str(w.errors) for w in warnings)
