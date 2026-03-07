"""Tests for framework-aware configuration resolution."""

from __future__ import annotations

from aes.frameworks import resolve_config


class TestResolveConfig:
    def test_api_base_config(self):
        config = resolve_config("api", [], "python")
        assert config is not None
        assert "API" in config.instructions_description or "api" in config.instructions_description.lower()
        skill_ids = [s.id for s in config.skills]
        assert "test-runner" in skill_ids

    def test_frontend_base_config(self):
        config = resolve_config("web-frontend", [], "typescript")
        assert config is not None
        assert "npm run *" in config.permissions_shell_execute

    def test_fullstack_base_config(self):
        config = resolve_config("fullstack", [], "typescript")
        assert config is not None
        skill_ids = [s.id for s in config.skills]
        assert "db-migrate" in skill_ids

    def test_cli_base_config(self):
        config = resolve_config("cli-tool", [], "python")
        assert config is not None
        assert "exit codes" in config.instructions_rules[1].lower() or "Exit codes" in config.instructions_rules[1]

    def test_library_base_config(self):
        config = resolve_config("library", [], "python")
        assert config is not None
        assert "contract" in config.instructions_rules[0].lower()

    def test_unknown_type_returns_none(self):
        config = resolve_config("unknown-type", [], "python")
        assert config is None

    def test_other_returns_none(self):
        config = resolve_config("other", [], "python")
        assert config is None


class TestFrameworkOverlays:
    def test_fastapi_overlay(self):
        config = resolve_config("api", ["fastapi"], "python")
        assert config is not None
        skill_ids = [s.id for s in config.skills]
        assert "db-migrate" in skill_ids
        # Check FastAPI-specific rules merged
        rules_text = " ".join(config.instructions_rules)
        assert "Pydantic" in rules_text
        # Check FastAPI-specific permissions
        assert "alembic *" in config.permissions_shell_execute

    def test_django_overlay(self):
        config = resolve_config("api", ["django"], "python")
        assert config is not None
        skill_ids = [s.id for s in config.skills]
        assert "db-migrate" in skill_ids
        rules_text = " ".join(config.instructions_rules)
        assert "Django ORM" in rules_text

    def test_nextjs_overlay(self):
        config = resolve_config("fullstack", ["nextjs"], "typescript")
        assert config is not None
        rules_text = " ".join(config.instructions_rules)
        assert "Server components" in rules_text
        assert "npm run *" in config.permissions_shell_execute

    def test_express_overlay(self):
        config = resolve_config("api", ["express"], "javascript")
        assert config is not None
        rules_text = " ".join(config.instructions_rules)
        assert "Middleware" in rules_text or "middleware" in rules_text

    def test_react_overlay(self):
        config = resolve_config("web-frontend", ["react"], "typescript")
        assert config is not None
        rules_text = " ".join(config.instructions_rules)
        assert "Hooks" in rules_text or "hooks" in rules_text

    def test_test_command_applied_to_skill(self):
        config = resolve_config("api", ["fastapi"], "python", test_command="python -m pytest -v")
        assert config is not None
        test_skill = next(s for s in config.skills if s.id == "test-runner")
        assert test_skill.trigger_command == "python -m pytest -v"

    def test_multiple_overlays_merge(self):
        config = resolve_config("api", ["fastapi", "sqlalchemy"], "python")
        assert config is not None
        # fastapi overlay should be applied (sqlalchemy has no overlay but is detected)
        rules_text = " ".join(config.instructions_rules)
        assert "Pydantic" in rules_text

    def test_no_duplicate_skills(self):
        config = resolve_config("fullstack", ["nextjs"], "typescript")
        assert config is not None
        skill_ids = [s.id for s in config.skills]
        # Should not have duplicates
        assert len(skill_ids) == len(set(skill_ids))

    def test_permissions_deduplicated(self):
        config = resolve_config("fullstack", ["nextjs"], "typescript")
        assert config is not None
        # npm run * should appear only once
        count = config.permissions_shell_execute.count("npm run *")
        assert count == 1
