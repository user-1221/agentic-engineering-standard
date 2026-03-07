"""Smart project analyzer for aes init.

Scans a project directory to detect language, frameworks, project type,
and other signals that inform the scaffolding of .agent/ configuration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Known frameworks per language (dependency name -> framework label)
# ---------------------------------------------------------------------------

_PYTHON_FRAMEWORKS: Dict[str, str] = {
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "streamlit": "streamlit",
    "celery": "celery",
    "scrapy": "scrapy",
    "pytorch": "pytorch",
    "torch": "pytorch",
    "tensorflow": "tensorflow",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "pandas": "pandas",
    "airflow": "airflow",
    "apache-airflow": "airflow",
    "prefect": "prefect",
    "luigi": "luigi",
    "click": "click",
    "typer": "typer",
    "sqlalchemy": "sqlalchemy",
    "alembic": "alembic",
}

_JS_FRAMEWORKS: Dict[str, str] = {
    "next": "nextjs",
    "react": "react",
    "vue": "vue",
    "nuxt": "nuxt",
    "svelte": "svelte",
    "@sveltejs/kit": "sveltekit",
    "express": "express",
    "@nestjs/core": "nestjs",
    "fastify": "fastify",
    "hono": "hono",
    "angular": "angular",
    "@angular/core": "angular",
    "electron": "electron",
    "prisma": "prisma",
    "@prisma/client": "prisma",
    "drizzle-orm": "drizzle",
}

_GO_FRAMEWORKS: Dict[str, str] = {
    "github.com/gin-gonic/gin": "gin",
    "github.com/gofiber/fiber": "fiber",
    "github.com/labstack/echo": "echo",
    "github.com/spf13/cobra": "cobra",
    "google.golang.org/grpc": "grpc",
    "github.com/gorilla/mux": "gorilla",
}

_RUST_FRAMEWORKS: Dict[str, str] = {
    "actix-web": "actix-web",
    "rocket": "rocket",
    "axum": "axum",
    "tokio": "tokio",
    "clap": "clap",
    "warp": "warp",
}

# ---------------------------------------------------------------------------
# Framework -> project type classification
# ---------------------------------------------------------------------------

_API_FRAMEWORKS = {
    "fastapi", "django", "flask", "express", "nestjs", "fastify",
    "hono", "gin", "fiber", "echo", "gorilla", "actix-web", "rocket",
    "axum", "warp",
}
_FRONTEND_FRAMEWORKS = {"react", "vue", "svelte", "angular"}
_FULLSTACK_FRAMEWORKS = {"nextjs", "nuxt", "sveltekit"}
_CLI_FRAMEWORKS = {"click", "typer", "cobra", "clap"}
_ML_FRAMEWORKS = {"pytorch", "tensorflow", "scikit-learn"}
_DATA_FRAMEWORKS = {"airflow", "prefect", "luigi", "pandas"}


# ---------------------------------------------------------------------------
# Result data class
# ---------------------------------------------------------------------------

@dataclass
class ProjectAnalysis:
    """Result of analyzing a project directory."""

    name: str
    language: str
    frameworks: List[str] = field(default_factory=list)
    project_type: str = "other"
    has_tests: bool = False
    has_ci: bool = False
    has_docker: bool = False
    has_database: bool = False
    test_command: Optional[str] = None
    build_command: Optional[str] = None
    source_dirs: List[str] = field(default_factory=list)
    existing_agent_configs: Dict[str, Path] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Language detection (improved from init.py)
# ---------------------------------------------------------------------------

_LANGUAGE_MARKERS = [
    ("python", ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"]),
    ("typescript", ["tsconfig.json"]),
    ("javascript", ["package.json"]),
    ("go", ["go.mod"]),
    ("rust", ["Cargo.toml"]),
    ("java", ["pom.xml", "build.gradle", "build.gradle.kts"]),
]


def _detect_language(root: Path) -> str:
    for language, markers in _LANGUAGE_MARKERS:
        for marker in markers:
            if (root / marker).exists():
                return language
    return "other"


# ---------------------------------------------------------------------------
# Framework detection per language
# ---------------------------------------------------------------------------

def _parse_python_deps(root: Path) -> List[str]:
    """Extract dependency names from Python project files."""
    deps: List[str] = []

    # pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            # Simple regex extraction from dependencies list
            # Matches lines like: "fastapi>=0.100", 'django', etc.
            in_deps = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped in ("dependencies = [", "[project.dependencies]"):
                    in_deps = True
                    continue
                if in_deps:
                    if stripped == "]" or (stripped.startswith("[") and not stripped.startswith("[")):
                        in_deps = False
                        continue
                    match = re.match(r'["\']([a-zA-Z0-9_-]+)', stripped)
                    if match:
                        deps.append(match.group(1).lower())
        except (OSError, UnicodeDecodeError):
            pass

    # requirements.txt
    reqtxt = root / "requirements.txt"
    if reqtxt.exists():
        try:
            for line in reqtxt.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    match = re.match(r"([a-zA-Z0-9_-]+)", line)
                    if match:
                        deps.append(match.group(1).lower())
        except (OSError, UnicodeDecodeError):
            pass

    return deps


def _parse_js_deps(root: Path) -> List[str]:
    """Extract dependency names from package.json."""
    import json

    pkg = root / "package.json"
    if not pkg.exists():
        return []
    try:
        data = json.loads(pkg.read_text())
        deps = list(data.get("dependencies", {}).keys())
        deps += list(data.get("devDependencies", {}).keys())
        return [d.lower() for d in deps]
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []


def _parse_go_deps(root: Path) -> List[str]:
    """Extract module paths from go.mod require block."""
    gomod = root / "go.mod"
    if not gomod.exists():
        return []
    try:
        content = gomod.read_text()
        deps: List[str] = []
        in_require = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("require ("):
                in_require = True
                continue
            if in_require:
                if stripped == ")":
                    in_require = False
                    continue
                parts = stripped.split()
                if parts:
                    deps.append(parts[0])
        return deps
    except (OSError, UnicodeDecodeError):
        return []


def _parse_rust_deps(root: Path) -> List[str]:
    """Extract crate names from Cargo.toml [dependencies]."""
    cargo = root / "Cargo.toml"
    if not cargo.exists():
        return []
    try:
        content = cargo.read_text()
        deps: List[str] = []
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "[dependencies]":
                in_deps = True
                continue
            if in_deps:
                if stripped.startswith("["):
                    in_deps = False
                    continue
                match = re.match(r"([a-zA-Z0-9_-]+)\s*=", stripped)
                if match:
                    deps.append(match.group(1).lower())
        return deps
    except (OSError, UnicodeDecodeError):
        return []


def _detect_frameworks(root: Path, language: str) -> List[str]:
    """Detect frameworks from dependency files."""
    framework_map: Dict[str, str]
    raw_deps: List[str]

    if language == "python":
        raw_deps = _parse_python_deps(root)
        framework_map = _PYTHON_FRAMEWORKS
    elif language in ("javascript", "typescript"):
        raw_deps = _parse_js_deps(root)
        framework_map = _JS_FRAMEWORKS
    elif language == "go":
        raw_deps = _parse_go_deps(root)
        framework_map = _GO_FRAMEWORKS
    elif language == "rust":
        raw_deps = _parse_rust_deps(root)
        framework_map = _RUST_FRAMEWORKS
    else:
        return []

    seen = set()
    frameworks: List[str] = []
    for dep in raw_deps:
        label = framework_map.get(dep)
        if label and label not in seen:
            seen.add(label)
            frameworks.append(label)

    return frameworks


# ---------------------------------------------------------------------------
# Project type classification
# ---------------------------------------------------------------------------

def _classify_project_type(frameworks: List[str], root: Path) -> str:
    """Classify project type from frameworks and directory structure."""
    fw_set = set(frameworks)

    # Check for fullstack first (most specific)
    if fw_set & _FULLSTACK_FRAMEWORKS:
        return "fullstack"

    # Check for ML
    if fw_set & _ML_FRAMEWORKS:
        return "ml"

    # Check for data pipeline
    if fw_set & _DATA_FRAMEWORKS:
        return "data-pipeline"

    # Check for CLI tool
    if fw_set & _CLI_FRAMEWORKS:
        return "cli-tool"

    # API with frontend = fullstack
    has_api = bool(fw_set & _API_FRAMEWORKS)
    has_frontend = bool(fw_set & _FRONTEND_FRAMEWORKS)
    if has_api and has_frontend:
        return "fullstack"
    if has_api:
        return "api"
    if has_frontend:
        return "web-frontend"

    # Check for devops by directory structure
    if (root / "terraform").is_dir() or list(root.glob("*.tf")):
        return "devops"
    if (root / "ansible").is_dir() or (root / "playbook.yml").exists():
        return "devops"

    # Check for library (no entry point, has package config)
    has_pkg = (
        (root / "pyproject.toml").exists()
        or (root / "package.json").exists()
        or (root / "Cargo.toml").exists()
    )
    has_entry = (
        (root / "main.py").exists()
        or (root / "app.py").exists()
        or (root / "src" / "main.py").exists()
        or (root / "src" / "index.ts").exists()
        or (root / "src" / "index.js").exists()
        or (root / "cmd").is_dir()
        or (root / "src" / "main.rs").exists()
    )
    if has_pkg and not has_entry and not frameworks:
        return "library"

    return "other"


# ---------------------------------------------------------------------------
# Signal detection
# ---------------------------------------------------------------------------

def _detect_tests(root: Path, language: str) -> tuple:
    """Detect test directory and infer test command. Returns (has_tests, command)."""
    test_dirs = ["tests", "test", "__tests__", "spec"]
    has_tests = any((root / d).is_dir() for d in test_dirs)

    if not has_tests:
        # Check for test files in src
        has_tests = bool(
            list(root.glob("**/test_*.py"))[:1]
            or list(root.glob("**/*.test.ts"))[:1]
            or list(root.glob("**/*.test.js"))[:1]
            or list(root.glob("**/*_test.go"))[:1]
        )

    command: Optional[str] = None
    if has_tests:
        if language == "python":
            command = "python -m pytest"
        elif language in ("javascript", "typescript"):
            # Check package.json for test script
            import json
            pkg = root / "package.json"
            if pkg.exists():
                try:
                    data = json.loads(pkg.read_text())
                    if "test" in data.get("scripts", {}):
                        command = "npm run test"
                except (OSError, json.JSONDecodeError):
                    pass
            if not command:
                command = "npm test"
        elif language == "go":
            command = "go test ./..."
        elif language == "rust":
            command = "cargo test"

    return has_tests, command


def _detect_build_command(root: Path, language: str) -> Optional[str]:
    """Infer build command from project files."""
    import json

    if language in ("javascript", "typescript"):
        pkg = root / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text())
                if "build" in data.get("scripts", {}):
                    return "npm run build"
            except (OSError, json.JSONDecodeError):
                pass
    elif language == "go":
        return "go build ./..."
    elif language == "rust":
        return "cargo build"
    return None


def _detect_existing_configs(root: Path) -> Dict[str, Path]:
    """Find existing agent configuration files."""
    configs: Dict[str, Path] = {}

    candidates = {
        "claude": root / "CLAUDE.md",
        "cursor": root / ".cursorrules",
        "copilot": root / ".github" / "copilot-instructions.md",
        "windsurf": root / ".windsurfrules",
    }
    for tool, path in candidates.items():
        if path.exists() and path.stat().st_size > 0:
            configs[tool] = path

    return configs


def _detect_source_dirs(root: Path) -> List[str]:
    """Detect common source directories."""
    candidates = ["src", "lib", "app", "pkg", "cmd", "internal", "api"]
    return [d for d in candidates if (root / d).is_dir()]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def analyze_project(root: Path) -> ProjectAnalysis:
    """Analyze a project directory and return structured findings.

    This is the main entry point.  It detects language, frameworks,
    project type, and various project signals without requiring any
    user input.
    """
    name_raw = root.name
    name = re.sub(r"[^a-z0-9]+", "-", name_raw.lower()).strip("-") or "my-project"

    language = _detect_language(root)
    frameworks = _detect_frameworks(root, language)
    project_type = _classify_project_type(frameworks, root)

    has_tests, test_command = _detect_tests(root, language)
    build_command = _detect_build_command(root, language)

    has_ci = (
        (root / ".github" / "workflows").is_dir()
        or (root / ".gitlab-ci.yml").exists()
        or (root / "Jenkinsfile").exists()
        or (root / ".circleci").is_dir()
    )

    has_docker = (
        (root / "Dockerfile").exists()
        or (root / "docker-compose.yml").exists()
        or (root / "docker-compose.yaml").exists()
    )

    has_database = (
        (root / "migrations").is_dir()
        or (root / "alembic").is_dir()
        or (root / "alembic.ini").exists()
        or (root / "prisma").is_dir()
        or (root / "drizzle").is_dir()
    )

    return ProjectAnalysis(
        name=name,
        language=language,
        frameworks=frameworks,
        project_type=project_type,
        has_tests=has_tests,
        has_ci=has_ci,
        has_docker=has_docker,
        has_database=has_database,
        test_command=test_command,
        build_command=build_command,
        source_dirs=_detect_source_dirs(root),
        existing_agent_configs=_detect_existing_configs(root),
    )
