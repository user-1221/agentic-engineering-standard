"""Tests for aes validate command and schema validation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from aes.validator import validate_file, validate_agent_dir, load_schema


EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


class TestLoadSchema:
    def test_load_known_schema(self):
        schema = load_schema("agent")
        assert schema["title"] == "AES Agent Manifest"

    def test_load_unknown_schema_raises(self):
        with pytest.raises(ValueError, match="Unknown schema type"):
            load_schema("nonexistent")


class TestValidateFile:
    def test_valid_agent_yaml(self):
        path = EXAMPLES_DIR / "ml-pipeline" / ".agent" / "agent.yaml"
        result = validate_file(path, "agent")
        assert result.valid, result.errors

    def test_valid_skill_yaml(self):
        path = EXAMPLES_DIR / "ml-pipeline" / ".agent" / "skills" / "discover.skill.yaml"
        result = validate_file(path, "skill")
        assert result.valid, result.errors

    def test_valid_workflow_yaml(self):
        path = EXAMPLES_DIR / "ml-pipeline" / ".agent" / "workflows" / "pipeline.yaml"
        result = validate_file(path, "workflow")
        assert result.valid, result.errors

    def test_valid_registry_yaml(self):
        path = EXAMPLES_DIR / "ml-pipeline" / ".agent" / "registry" / "models.yaml"
        result = validate_file(path, "registry")
        assert result.valid, result.errors

    def test_valid_permissions_yaml(self):
        path = EXAMPLES_DIR / "ml-pipeline" / ".agent" / "permissions.yaml"
        result = validate_file(path, "permissions")
        assert result.valid, result.errors

    def test_invalid_yaml(self, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("not: a: valid: yaml: [")
        result = validate_file(bad_file, "agent")
        assert not result.valid
        assert any("parse" in e.lower() or "scan" in e.lower() for e in result.errors)

    def test_missing_required_fields(self, tmp_path):
        bad_file = tmp_path / "bad_agent.yaml"
        bad_file.write_text(yaml.dump({"aes": "1.0"}))
        result = validate_file(bad_file, "agent")
        assert not result.valid
        assert any("name" in e for e in result.errors)


class TestValidateAgentDir:
    def test_ml_pipeline_validates(self):
        agent_dir = EXAMPLES_DIR / "ml-pipeline" / ".agent"
        results = validate_agent_dir(agent_dir)
        for r in results:
            assert r.valid, f"{r.file_path}: {r.errors}"

    def test_web_app_validates(self):
        agent_dir = EXAMPLES_DIR / "web-app" / ".agent"
        results = validate_agent_dir(agent_dir)
        for r in results:
            assert r.valid, f"{r.file_path}: {r.errors}"

    def test_devops_validates(self):
        agent_dir = EXAMPLES_DIR / "devops" / ".agent"
        results = validate_agent_dir(agent_dir)
        for r in results:
            assert r.valid, f"{r.file_path}: {r.errors}"

    def test_missing_agent_yaml(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        results = validate_agent_dir(agent_dir)
        assert len(results) == 1
        assert not results[0].valid
        assert "required" in results[0].errors[0].lower()

    def test_missing_referenced_files(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        manifest = {
            "aes": "1.0",
            "name": "test-project",
            "version": "1.0.0",
            "description": "Test",
            "agent": {
                "instructions": "instructions.md",
                "permissions": "permissions.yaml",
            },
            "skills": [
                {
                    "id": "missing-skill",
                    "manifest": "skills/missing.skill.yaml",
                    "runbook": "skills/missing.md",
                }
            ],
        }
        (agent_dir / "agent.yaml").write_text(yaml.dump(manifest))
        results = validate_agent_dir(agent_dir)
        # Should have failures for missing files
        failed = [r for r in results if not r.valid]
        assert len(failed) >= 1


class TestSchemaRejection:
    """Test that schemas correctly reject invalid data."""

    def test_agent_rejects_bad_name(self, tmp_path):
        bad = tmp_path / "agent.yaml"
        bad.write_text(yaml.dump({
            "aes": "1.0",
            "name": "UPPERCASE-BAD",
            "version": "1.0.0",
            "description": "test",
        }))
        result = validate_file(bad, "agent")
        assert not result.valid

    def test_skill_rejects_missing_id(self, tmp_path):
        bad = tmp_path / "skill.yaml"
        bad.write_text(yaml.dump({
            "aes_skill": "1.0",
            "name": "Test",
            "version": "1.0.0",
            "description": "test",
        }))
        result = validate_file(bad, "skill")
        assert not result.valid

    def test_workflow_rejects_no_states(self, tmp_path):
        bad = tmp_path / "workflow.yaml"
        bad.write_text(yaml.dump({
            "aes_workflow": "1.0",
            "id": "test",
            "entity": "thing",
            "states": {},
            "transitions": [{"from": "a", "to": "b"}],
        }))
        result = validate_file(bad, "workflow")
        assert not result.valid


# ---------------------------------------------------------------------------
# Skill dependency graph validation
# ---------------------------------------------------------------------------

class TestSkillDependencyGraph:

    def test_valid_deps_no_errors(self, tmp_path):
        """Valid depends_on/blocks references produce no errors."""
        agent_dir = tmp_path / ".agent"
        _make_agent_with_skills(agent_dir, [
            {"id": "discover", "blocks": ["examine"]},
            {"id": "examine", "depends_on": ["discover"], "blocks": ["train"]},
            {"id": "train", "depends_on": ["examine"]},
        ])
        results = validate_agent_dir(agent_dir)
        failed = [r for r in results if not r.valid]
        assert len(failed) == 0, [r.errors for r in failed]

    def test_dangling_depends_on_is_warning(self, tmp_path):
        """depends_on referencing a non-existent skill is a warning."""
        agent_dir = tmp_path / ".agent"
        _make_agent_with_skills(agent_dir, [
            {"id": "train", "depends_on": ["nonexistent"]},
        ])
        results = validate_agent_dir(agent_dir)
        # Should not fail — vendored skills may reference uninstalled deps
        failed = [r for r in results if not r.valid]
        assert len(failed) == 0
        # But should have a warning message
        all_errors = [e for r in results for e in r.errors]
        assert any("depends_on references skill not in this project" in e for e in all_errors)

    def test_dangling_blocks_is_warning(self, tmp_path):
        """blocks referencing a non-existent skill is a warning (valid=True)."""
        agent_dir = tmp_path / ".agent"
        _make_agent_with_skills(agent_dir, [
            {"id": "discover", "blocks": ["ghost"]},
        ])
        results = validate_agent_dir(agent_dir)
        # Should not fail — blocks are informational
        failed = [r for r in results if not r.valid]
        assert len(failed) == 0
        # But should have a warning message
        all_errors = [e for r in results for e in r.errors]
        assert any("blocks references skill not in this project" in e for e in all_errors)

    def test_cycle_detection(self, tmp_path):
        """Circular depends_on is caught."""
        agent_dir = tmp_path / ".agent"
        _make_agent_with_skills(agent_dir, [
            {"id": "alpha", "depends_on": ["beta"]},
            {"id": "beta", "depends_on": ["alpha"]},
        ])
        results = validate_agent_dir(agent_dir)
        failed = [r for r in results if not r.valid]
        assert any("Circular dependency" in e for r in failed for e in r.errors)

    def test_self_cycle_detection(self, tmp_path):
        """A skill depending on itself is caught."""
        agent_dir = tmp_path / ".agent"
        _make_agent_with_skills(agent_dir, [
            {"id": "loop", "depends_on": ["loop"]},
        ])
        results = validate_agent_dir(agent_dir)
        failed = [r for r in results if not r.valid]
        assert any("Circular dependency" in e for r in failed for e in r.errors)

    def test_object_style_depends_on(self, tmp_path):
        """depends_on with {skill: "x"} object form is validated (warning)."""
        agent_dir = tmp_path / ".agent"
        skills_dir = agent_dir / "skills"
        skills_dir.mkdir(parents=True)

        (skills_dir / "a.skill.yaml").write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": "a",
            "name": "A",
            "version": "1.0.0",
            "description": "Skill A",
            "depends_on": [{"skill": "missing", "version": "^1.0"}],
        }))
        (agent_dir / "agent.yaml").write_text(yaml.dump({
            "aes": "1.0",
            "name": "obj-dep-test",
            "version": "1.0.0",
            "description": "Test",
            "skills": [{"id": "a", "manifest": "skills/a.skill.yaml"}],
        }))
        results = validate_agent_dir(agent_dir)
        all_errors = [e for r in results for e in r.errors]
        assert any("depends_on references skill not in this project" in e for e in all_errors)

    def test_ml_pipeline_deps_valid(self):
        """The ml-pipeline example has valid deps (examine depends_on discover, etc.)."""
        agent_dir = EXAMPLES_DIR / "ml-pipeline" / ".agent"
        results = validate_agent_dir(agent_dir)
        for r in results:
            assert r.valid, f"{r.file_path}: {r.errors}"


# ---------------------------------------------------------------------------
# Skill quality checks (warnings)
# ---------------------------------------------------------------------------

class TestSkillQualityChecks:

    def test_todo_description_warns(self, tmp_path):
        """A skill with 'TODO' in description triggers a quality warning."""
        agent_dir = tmp_path / ".agent"
        _make_agent_with_skills(agent_dir, [
            {"id": "bad-desc", "description": "TODO: describe what this does"},
        ])
        results = validate_agent_dir(agent_dir)
        warnings = [r for r in results if r.valid and r.errors]
        assert any("TODO" in e for r in warnings for e in r.errors)

    def test_short_description_warns(self, tmp_path):
        """A skill with description < 20 chars triggers a quality warning."""
        agent_dir = tmp_path / ".agent"
        _make_agent_with_skills(agent_dir, [
            {"id": "short", "description": "Do stuff"},
        ])
        results = validate_agent_dir(agent_dir)
        warnings = [r for r in results if r.valid and r.errors]
        assert any("aim for 20+" in e for r in warnings for e in r.errors)

    def test_good_description_no_warning(self, tmp_path):
        """A skill with a good description has no quality warnings."""
        agent_dir = tmp_path / ".agent"
        _make_agent_with_skills(agent_dir, [
            {"id": "good", "description": "Find new public datasets from APIs and filter by quality criteria"},
        ])
        results = validate_agent_dir(agent_dir)
        quality_warnings = [
            r for r in results if r.valid and r.errors
            and any("description" in e.lower() for e in r.errors)
        ]
        assert len(quality_warnings) == 0

    def test_empty_tags_warns(self, tmp_path):
        """A skill with empty string in tags triggers a warning."""
        agent_dir = tmp_path / ".agent"
        skills_dir = agent_dir / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "etag.skill.yaml").write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": "etag",
            "name": "Empty Tag",
            "version": "1.0.0",
            "description": "A skill with empty tag values for testing",
            "tags": ["good-tag", "", "another-good"],
        }))
        (agent_dir / "agent.yaml").write_text(yaml.dump({
            "aes": "1.0",
            "name": "tag-test",
            "version": "1.0.0",
            "description": "Test",
            "skills": [{"id": "etag", "manifest": "skills/etag.skill.yaml"}],
        }))
        results = validate_agent_dir(agent_dir)
        warnings = [r for r in results if r.valid and r.errors]
        assert any("empty tag" in e.lower() for r in warnings for e in r.errors)

    def test_oversized_runbook_warns(self, tmp_path):
        """A runbook > 5000 words triggers a warning."""
        agent_dir = tmp_path / ".agent"
        skills_dir = agent_dir / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "big.skill.yaml").write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": "big",
            "name": "Big Runbook",
            "version": "1.0.0",
            "description": "A skill with a very large runbook for testing",
        }))
        # Create a runbook with > 5000 words
        (skills_dir / "big.md").write_text("word " * 5500)
        (agent_dir / "agent.yaml").write_text(yaml.dump({
            "aes": "1.0",
            "name": "runbook-test",
            "version": "1.0.0",
            "description": "Test",
            "skills": [{
                "id": "big",
                "manifest": "skills/big.skill.yaml",
                "runbook": "skills/big.md",
            }],
        }))
        results = validate_agent_dir(agent_dir)
        warnings = [r for r in results if r.valid and r.errors]
        assert any("5000" in e for r in warnings for e in r.errors)

    def test_bom_validates_in_agent_dir(self, tmp_path):
        """bom.yaml is validated when present in .agent/ directory."""
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text(yaml.dump({
            "aes": "1.2",
            "name": "bom-test",
            "version": "1.0.0",
            "description": "Test",
        }))
        (agent_dir / "bom.yaml").write_text(yaml.dump({
            "aes_bom": "1.2",
            "models": [{"name": "test", "provider": "test"}],
        }))
        results = validate_agent_dir(agent_dir)
        bom_results = [r for r in results if r.schema_type == "bom"]
        assert len(bom_results) == 1
        assert bom_results[0].valid

    def test_skill_count_over_50_warns(self, tmp_path):
        """More than 50 skills triggers a warning."""
        agent_dir = tmp_path / ".agent"
        skills_data = [
            {"id": f"skill-{i}", "description": f"Skill number {i} for testing limits"}
            for i in range(55)
        ]
        _make_agent_with_skills(agent_dir, skills_data)
        results = validate_agent_dir(agent_dir)
        warnings = [r for r in results if r.valid and r.errors]
        assert any("55 skills" in e for r in warnings for e in r.errors)


def _make_agent_with_skills(agent_dir, skills_data):
    """Helper: create agent.yaml + skill manifests for dep/quality validation tests.

    *skills_data* is a list of dicts with keys: id, depends_on, blocks, description.
    """
    agent_dir.mkdir(parents=True, exist_ok=True)
    skills_dir = agent_dir / "skills"
    skills_dir.mkdir(exist_ok=True)

    skill_refs = []
    for sd in skills_data:
        sid = sd["id"]
        manifest_name = f"{sid}.skill.yaml"
        skill_file = skills_dir / manifest_name
        skill_file.write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": sid,
            "name": sid.title(),
            "version": "1.0.0",
            "description": sd.get("description", f"Skill {sid}"),
            "depends_on": sd.get("depends_on", []),
            "blocks": sd.get("blocks", []),
        }))
        skill_refs.append({"id": sid, "manifest": f"skills/{manifest_name}"})

    (agent_dir / "agent.yaml").write_text(yaml.dump({
        "aes": "1.0",
        "name": "dep-test",
        "version": "1.0.0",
        "description": "Dependency test project",
        "skills": skill_refs,
    }))


# ---------------------------------------------------------------------------
# Schema acceptance of new fields
# ---------------------------------------------------------------------------

class TestNewSchemaFields:
    """Ensure schemas accept the new fields (negative_triggers, activation, allowed_tools)."""

    def test_skill_with_negative_triggers(self, tmp_path):
        bad = tmp_path / "skill.yaml"
        bad.write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": "test-neg",
            "name": "Test Negative Triggers",
            "version": "1.0.0",
            "description": "A test skill with negative triggers for validation",
            "negative_triggers": [
                "Do NOT use for CSV imports",
                "Do NOT use without API keys",
            ],
        }))
        result = validate_file(bad, "skill")
        assert result.valid, result.errors

    def test_skill_with_activation_auto(self, tmp_path):
        f = tmp_path / "skill.yaml"
        f.write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": "test-auto",
            "name": "Test Auto Activation",
            "version": "1.0.0",
            "description": "A skill with auto activation mode for validation",
            "activation": "auto",
        }))
        result = validate_file(f, "skill")
        assert result.valid, result.errors

    def test_skill_with_activation_hybrid(self, tmp_path):
        f = tmp_path / "skill.yaml"
        f.write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": "test-hybrid",
            "name": "Test Hybrid Activation",
            "version": "1.0.0",
            "description": "A skill with hybrid activation mode for validation",
            "activation": "hybrid",
        }))
        result = validate_file(f, "skill")
        assert result.valid, result.errors

    def test_skill_with_invalid_activation_rejected(self, tmp_path):
        f = tmp_path / "skill.yaml"
        f.write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": "test-bad-act",
            "name": "Test Bad Activation",
            "version": "1.0.0",
            "description": "A skill with invalid activation mode for validation",
            "activation": "invalid",
        }))
        result = validate_file(f, "skill")
        assert not result.valid

    def test_skill_with_allowed_tools(self, tmp_path):
        f = tmp_path / "skill.yaml"
        f.write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": "test-perms",
            "name": "Test Permissions",
            "version": "1.0.0",
            "description": "A skill with per-skill permissions for validation",
            "allowed_tools": {
                "shell": True,
                "files": {
                    "read": True,
                    "write": ["src/**", "config/**"],
                },
                "network": False,
                "mcp_servers": ["fetch"],
            },
        }))
        result = validate_file(f, "skill")
        assert result.valid, result.errors

    def test_skill_with_allowed_tools_invalid_field_rejected(self, tmp_path):
        f = tmp_path / "skill.yaml"
        f.write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": "test-bad-perms",
            "name": "Test Bad Permissions",
            "version": "1.0.0",
            "description": "A skill with invalid allowed_tools field for validation",
            "allowed_tools": {
                "shell": True,
                "dangerous_field": True,
            },
        }))
        result = validate_file(f, "skill")
        assert not result.valid

    def test_description_over_1024_rejected(self, tmp_path):
        f = tmp_path / "skill.yaml"
        f.write_text(yaml.dump({
            "aes_skill": "1.0",
            "id": "test-long-desc",
            "name": "Test Long Description",
            "version": "1.0.0",
            "description": "x" * 1025,
        }))
        result = validate_file(f, "skill")
        assert not result.valid


# ---------------------------------------------------------------------------
# Template validation (dogfooded templates)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# v1.2 schema validation tests
# ---------------------------------------------------------------------------

class TestAgentManifestV12:
    """Test agent.yaml accepts new v1.2 fields (models, provenance, interop)."""

    def test_agent_with_models(self, tmp_path):
        f = tmp_path / "agent.yaml"
        f.write_text(yaml.dump({
            "aes": "1.2",
            "name": "test-models",
            "version": "1.0.0",
            "description": "Test agent with models section",
            "models": [
                {"name": "claude-sonnet-4", "provider": "anthropic", "purpose": "primary"},
            ],
        }))
        result = validate_file(f, "agent")
        assert result.valid, result.errors

    def test_agent_with_provenance(self, tmp_path):
        f = tmp_path / "agent.yaml"
        f.write_text(yaml.dump({
            "aes": "1.2",
            "name": "test-provenance",
            "version": "1.0.0",
            "description": "Test agent with provenance section",
            "provenance": {
                "created_by": "hiro",
                "created_at": "2026-03-01",
                "source": "https://github.com/example/repo",
            },
        }))
        result = validate_file(f, "agent")
        assert result.valid, result.errors

    def test_agent_with_interop(self, tmp_path):
        f = tmp_path / "agent.yaml"
        f.write_text(yaml.dump({
            "aes": "1.2",
            "name": "test-interop",
            "version": "1.0.0",
            "description": "Test agent with interop section",
            "interop": {
                "a2a_card": "https://example.com/.well-known/agent.json",
                "mcp_servers": [
                    {"name": "fetch", "transport": "stdio", "command": "npx"},
                ],
            },
        }))
        result = validate_file(f, "agent")
        assert result.valid, result.errors

    def test_model_invalid_purpose_rejected(self, tmp_path):
        f = tmp_path / "agent.yaml"
        f.write_text(yaml.dump({
            "aes": "1.2",
            "name": "test-bad-purpose",
            "version": "1.0.0",
            "description": "Test agent with invalid model purpose",
            "models": [
                {"name": "test", "provider": "test", "purpose": "invalid"},
            ],
        }))
        result = validate_file(f, "agent")
        assert not result.valid

    def test_model_missing_provider_rejected(self, tmp_path):
        f = tmp_path / "agent.yaml"
        f.write_text(yaml.dump({
            "aes": "1.2",
            "name": "test-no-provider",
            "version": "1.0.0",
            "description": "Test agent with model missing provider",
            "models": [
                {"name": "test"},
            ],
        }))
        result = validate_file(f, "agent")
        assert not result.valid

    def test_mcp_server_invalid_transport_rejected(self, tmp_path):
        f = tmp_path / "agent.yaml"
        f.write_text(yaml.dump({
            "aes": "1.2",
            "name": "test-bad-transport",
            "version": "1.0.0",
            "description": "Test agent with invalid MCP transport",
            "interop": {
                "mcp_servers": [
                    {"name": "fetch", "transport": "invalid"},
                ],
            },
        }))
        result = validate_file(f, "agent")
        assert not result.valid


class TestPermissionsV12:
    """Test permissions.yaml accepts new v1.2 fields."""

    def test_permissions_with_network(self, tmp_path):
        f = tmp_path / "permissions.yaml"
        f.write_text(yaml.dump({
            "aes_permissions": "1.2",
            "network": {
                "allow": ["https://api.anthropic.com/*"],
                "deny": ["*.internal.corp/*"],
            },
        }))
        result = validate_file(f, "permissions")
        assert result.valid, result.errors

    def test_permissions_with_process(self, tmp_path):
        f = tmp_path / "permissions.yaml"
        f.write_text(yaml.dump({
            "aes_permissions": "1.2",
            "process": {
                "allow": ["python", "node"],
                "deny": ["curl"],
            },
        }))
        result = validate_file(f, "permissions")
        assert result.valid, result.errors

    def test_permissions_with_inference(self, tmp_path):
        f = tmp_path / "permissions.yaml"
        f.write_text(yaml.dump({
            "aes_permissions": "1.2",
            "inference": {
                "routing": [
                    {"task": "code-gen", "models": ["claude-sonnet-4"]},
                ],
                "max_tokens_per_request": 4096,
                "max_requests_per_minute": 60,
            },
        }))
        result = validate_file(f, "permissions")
        assert result.valid, result.errors

    def test_permissions_with_data(self, tmp_path):
        f = tmp_path / "permissions.yaml"
        f.write_text(yaml.dump({
            "aes_permissions": "1.2",
            "data": {
                "classification": "internal",
                "retention_days": 90,
                "pii_handling": "prohibit",
            },
        }))
        result = validate_file(f, "permissions")
        assert result.valid, result.errors

    def test_data_invalid_classification_rejected(self, tmp_path):
        f = tmp_path / "permissions.yaml"
        f.write_text(yaml.dump({
            "aes_permissions": "1.2",
            "data": {"classification": "top-secret"},
        }))
        result = validate_file(f, "permissions")
        assert not result.valid

    def test_data_invalid_pii_handling_rejected(self, tmp_path):
        f = tmp_path / "permissions.yaml"
        f.write_text(yaml.dump({
            "aes_permissions": "1.2",
            "data": {"pii_handling": "ignore"},
        }))
        result = validate_file(f, "permissions")
        assert not result.valid


class TestBomSchema:
    """Test bom.schema.json validation."""

    def test_valid_bom(self, tmp_path):
        f = tmp_path / "bom.yaml"
        f.write_text(yaml.dump({
            "aes_bom": "1.2",
            "models": [{"name": "claude", "provider": "anthropic"}],
            "frameworks": [{"name": "catboost", "version": "1.2"}],
            "tools": [{"name": "fetch", "type": "mcp-server"}],
            "data_sources": [{"name": "openml", "type": "api"}],
        }))
        result = validate_file(f, "bom")
        assert result.valid, result.errors

    def test_bom_missing_version_rejected(self, tmp_path):
        f = tmp_path / "bom.yaml"
        f.write_text(yaml.dump({"models": []}))
        result = validate_file(f, "bom")
        assert not result.valid

    def test_bom_invalid_tool_type_rejected(self, tmp_path):
        f = tmp_path / "bom.yaml"
        f.write_text(yaml.dump({
            "aes_bom": "1.2",
            "tools": [{"name": "bad", "type": "invalid"}],
        }))
        result = validate_file(f, "bom")
        assert not result.valid

    def test_bom_invalid_data_source_type_rejected(self, tmp_path):
        f = tmp_path / "bom.yaml"
        f.write_text(yaml.dump({
            "aes_bom": "1.2",
            "data_sources": [{"name": "bad", "type": "invalid"}],
        }))
        result = validate_file(f, "bom")
        assert not result.valid

    def test_bom_empty_valid(self, tmp_path):
        f = tmp_path / "bom.yaml"
        f.write_text(yaml.dump({"aes_bom": "1.2"}))
        result = validate_file(f, "bom")
        assert result.valid, result.errors


class TestDecisionRecordSchema:
    """Test decision-record.schema.json validation."""

    def test_valid_decision_record(self, tmp_path):
        f = tmp_path / "dr-001.yaml"
        f.write_text(yaml.dump({
            "aes_decision": "1.2",
            "id": "dr-001",
            "timestamp": "2026-03-17T14:30:00Z",
            "summary": "Chose regression over multiclass",
            "context": "Wine quality dataset",
            "alternatives": [
                {"option": "multiclass", "reason_rejected": "Low F1"},
            ],
            "rationale": "Better for ordinal targets",
            "outcome": "CatBoost R2=0.511",
            "approval": {"status": "auto", "approved_by": None},
            "tags": ["ml"],
        }))
        result = validate_file(f, "decision-record")
        assert result.valid, result.errors

    def test_decision_record_missing_required(self, tmp_path):
        f = tmp_path / "dr-bad.yaml"
        f.write_text(yaml.dump({
            "aes_decision": "1.2",
            "id": "dr-001",
        }))
        result = validate_file(f, "decision-record")
        assert not result.valid

    def test_decision_record_invalid_approval_status(self, tmp_path):
        f = tmp_path / "dr-bad-status.yaml"
        f.write_text(yaml.dump({
            "aes_decision": "1.2",
            "id": "dr-001",
            "timestamp": "2026-03-17T14:30:00Z",
            "summary": "Test",
            "approval": {"status": "invalid"},
        }))
        result = validate_file(f, "decision-record")
        assert not result.valid

    def test_decision_record_bad_id_pattern(self, tmp_path):
        f = tmp_path / "dr-bad-id.yaml"
        f.write_text(yaml.dump({
            "aes_decision": "1.2",
            "id": "bad-id",
            "timestamp": "2026-03-17T14:30:00Z",
            "summary": "Test",
        }))
        result = validate_file(f, "decision-record")
        assert not result.valid

    def test_decision_record_minimal(self, tmp_path):
        f = tmp_path / "dr-minimal.yaml"
        f.write_text(yaml.dump({
            "aes_decision": "1.2",
            "id": "dr-001",
            "timestamp": "2026-03-17T14:30:00Z",
            "summary": "A minimal decision",
        }))
        result = validate_file(f, "decision-record")
        assert result.valid, result.errors

    def test_decision_records_validated_in_agent_dir(self, tmp_path):
        """Decision records in memory/decisions/ are validated by validate_agent_dir."""
        agent_dir = tmp_path / ".agent"
        decisions_dir = agent_dir / "memory" / "decisions"
        decisions_dir.mkdir(parents=True)
        (agent_dir / "agent.yaml").write_text(yaml.dump({
            "aes": "1.2",
            "name": "dr-test",
            "version": "1.0.0",
            "description": "Test",
        }))
        (decisions_dir / "dr-001-test.yaml").write_text(yaml.dump({
            "aes_decision": "1.2",
            "id": "dr-001",
            "timestamp": "2026-03-17T14:30:00Z",
            "summary": "Test decision",
        }))
        results = validate_agent_dir(agent_dir)
        dr_results = [r for r in results if r.schema_type == "decision-record"]
        assert len(dr_results) == 1
        assert dr_results[0].valid


class TestTemplatesValidate:
    """Ensure templates/ directories pass aes validate."""

    def test_ml_template_validates(self):
        agent_dir = TEMPLATES_DIR / "ml" / ".agent"
        results = validate_agent_dir(agent_dir)
        for r in results:
            assert r.valid, f"{r.file_path}: {r.errors}"

    def test_web_template_validates(self):
        agent_dir = TEMPLATES_DIR / "web" / ".agent"
        results = validate_agent_dir(agent_dir)
        for r in results:
            assert r.valid, f"{r.file_path}: {r.errors}"

    def test_devops_template_validates(self):
        agent_dir = TEMPLATES_DIR / "devops" / ".agent"
        results = validate_agent_dir(agent_dir)
        for r in results:
            assert r.valid, f"{r.file_path}: {r.errors}"
