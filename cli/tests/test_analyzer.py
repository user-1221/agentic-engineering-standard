"""Tests for the project analyzer."""

from __future__ import annotations

import json
from pathlib import Path

from aes.analyzer import analyze_project


class TestLanguageDetection:
    def test_detect_python(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        result = analyze_project(tmp_path)
        assert result.language == "python"

    def test_detect_typescript(self, tmp_path):
        (tmp_path / "tsconfig.json").write_text("{}\n")
        (tmp_path / "package.json").write_text("{}\n")
        result = analyze_project(tmp_path)
        assert result.language == "typescript"

    def test_detect_go(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/foo\n")
        result = analyze_project(tmp_path)
        assert result.language == "go"

    def test_detect_rust(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'foo'\n")
        result = analyze_project(tmp_path)
        assert result.language == "rust"

    def test_fallback_other(self, tmp_path):
        result = analyze_project(tmp_path)
        assert result.language == "other"


class TestFrameworkDetection:
    def test_detect_fastapi(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        (tmp_path / "requirements.txt").write_text("fastapi>=0.100\nuvicorn\nsqlalchemy\n")
        result = analyze_project(tmp_path)
        assert "fastapi" in result.frameworks
        assert "sqlalchemy" in result.frameworks

    def test_detect_django(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("django>=4.0\ncelery\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        result = analyze_project(tmp_path)
        assert "django" in result.frameworks

    def test_detect_nextjs(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {"next": "14.0.0", "react": "18.0.0"},
        }))
        (tmp_path / "tsconfig.json").write_text("{}\n")
        result = analyze_project(tmp_path)
        assert "nextjs" in result.frameworks

    def test_detect_express(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {"express": "4.18.0"},
        }))
        result = analyze_project(tmp_path)
        assert "express" in result.frameworks

    def test_detect_gin(self, tmp_path):
        (tmp_path / "go.mod").write_text(
            "module example.com/foo\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.0\n)\n"
        )
        result = analyze_project(tmp_path)
        assert "gin" in result.frameworks

    def test_detect_axum(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            "[package]\nname = 'foo'\n\n[dependencies]\naxum = \"0.7\"\ntokio = \"1\"\n"
        )
        result = analyze_project(tmp_path)
        assert "axum" in result.frameworks

    def test_no_frameworks_empty_project(self, tmp_path):
        result = analyze_project(tmp_path)
        assert result.frameworks == []


class TestProjectTypeClassification:
    def test_api_from_fastapi(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        result = analyze_project(tmp_path)
        assert result.project_type == "api"

    def test_fullstack_from_nextjs(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {"next": "14.0.0"},
        }))
        (tmp_path / "tsconfig.json").write_text("{}\n")
        result = analyze_project(tmp_path)
        assert result.project_type == "fullstack"

    def test_frontend_from_react(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {"react": "18.0.0"},
        }))
        (tmp_path / "tsconfig.json").write_text("{}\n")
        result = analyze_project(tmp_path)
        assert result.project_type == "web-frontend"

    def test_cli_from_click(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("click\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        result = analyze_project(tmp_path)
        assert result.project_type == "cli-tool"

    def test_ml_from_pytorch(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("torch\npandas\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        result = analyze_project(tmp_path)
        assert result.project_type == "ml"

    def test_devops_from_terraform(self, tmp_path):
        (tmp_path / "terraform").mkdir()
        (tmp_path / "terraform" / "main.tf").write_text("")
        result = analyze_project(tmp_path)
        assert result.project_type == "devops"

    def test_other_empty_project(self, tmp_path):
        result = analyze_project(tmp_path)
        assert result.project_type == "other"


class TestSignalDetection:
    def test_detect_tests_python(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        result = analyze_project(tmp_path)
        assert result.has_tests is True
        assert result.test_command == "python -m pytest"

    def test_detect_tests_js(self, tmp_path):
        (tmp_path / "__tests__").mkdir()
        (tmp_path / "package.json").write_text(json.dumps({
            "scripts": {"test": "jest"},
        }))
        result = analyze_project(tmp_path)
        assert result.has_tests is True
        assert result.test_command == "npm run test"

    def test_detect_ci(self, tmp_path):
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        result = analyze_project(tmp_path)
        assert result.has_ci is True

    def test_detect_docker(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
        result = analyze_project(tmp_path)
        assert result.has_docker is True

    def test_detect_database(self, tmp_path):
        (tmp_path / "alembic").mkdir()
        result = analyze_project(tmp_path)
        assert result.has_database is True

    def test_detect_existing_configs(self, tmp_path):
        (tmp_path / ".cursorrules").write_text("some rules")
        (tmp_path / "CLAUDE.md").write_text("some instructions")
        result = analyze_project(tmp_path)
        assert "cursor" in result.existing_agent_configs
        assert "claude" in result.existing_agent_configs

    def test_detect_source_dirs(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "lib").mkdir()
        result = analyze_project(tmp_path)
        assert "src" in result.source_dirs
        assert "lib" in result.source_dirs

    def test_name_kebab_case(self, tmp_path):
        project = tmp_path / "My Cool App"
        project.mkdir()
        result = analyze_project(project)
        assert result.name == "my-cool-app"
