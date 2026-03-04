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

def _make_agent_with_skills(agent_dir, skills_data):
    """Helper: create agent.yaml + skill manifests for dep validation tests.

    *skills_data* is a list of dicts with keys: id, depends_on, blocks.
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
            "description": f"Skill {sid}",
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
# Template validation (dogfooded templates)
# ---------------------------------------------------------------------------

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
