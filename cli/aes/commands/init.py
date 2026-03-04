"""aes init — Scaffold a .agent/ directory."""

from __future__ import annotations

import re
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Optional

import click
from jinja2 import Environment, FileSystemLoader
from rich.console import Console

from aes.config import (
    AGENT_DIR,
    AGENTIGNORE_FILE,
    LOCAL_EXAMPLE_FILE,
    LOCAL_FILE,
    SCAFFOLD_DIR,
    SKILLS_DIR,
    REGISTRY_DIR,
    WORKFLOWS_DIR,
    COMMANDS_DIR,
    MEMORY_DIR,
    OVERRIDES_DIR,
)
from aes.commands.sync import run_sync
from aes.domains import DOMAIN_CONFIGS

console = Console()


# ---------------------------------------------------------------------------
# Auto-detection helpers
# ---------------------------------------------------------------------------

_LANGUAGE_MARKERS = [
    ("python", ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"]),
    ("typescript", ["tsconfig.json"]),
    ("javascript", ["package.json"]),
    ("go", ["go.mod"]),
    ("rust", ["Cargo.toml"]),
    ("java", ["pom.xml", "build.gradle", "build.gradle.kts"]),
]


def _detect_language(project_root: Path) -> str:
    """Auto-detect the primary language from marker files in *project_root*."""
    for language, markers in _LANGUAGE_MARKERS:
        for marker in markers:
            if (project_root / marker).exists():
                return language
    return "other"


def _detect_name(project_root: Path) -> str:
    """Derive a kebab-case project name from the directory name."""
    raw = project_root.name
    kebab = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return kebab or "my-project"


def _render_template(env: Environment, template_name: str, context: dict) -> str:
    """Render a Jinja2 template with context."""
    tmpl = env.get_template(template_name)
    return tmpl.render(**context)


def _init_from_registry(source: str, project_root: Path) -> None:
    """Initialize a project from a registry template.

    *source* is a registry reference like ``aes-hub/ml-pipeline@^2.0``.
    Downloads the template tarball and extracts its ``.agent/`` directory.
    """
    from aes.registry import (
        parse_registry_source,
        fetch_index,
        resolve_version,
        download_package,
    )

    name, version_spec = parse_registry_source(source)

    # Fetch index and resolve version
    try:
        index = fetch_index()
    except Exception as exc:
        raise click.ClickException(f"Failed to fetch registry: {exc}")

    pkg = index.get("packages", {}).get(name)
    if not pkg:
        raise click.ClickException(f"Package '{name}' not found in registry")

    available = list(pkg.get("versions", {}).keys())
    version = resolve_version(version_spec, available)
    if not version:
        raise click.ClickException(
            f"No version of '{name}' matching '{version_spec}'. "
            f"Available: {', '.join(available)}"
        )

    ver_info = pkg["versions"][version]

    # Check for existing .agent/ directory
    agent_dir = project_root / AGENT_DIR
    if agent_dir.exists():
        console.print(f"[yellow]Warning:[/] {AGENT_DIR}/ already exists at {project_root}")
        if not click.confirm("Overwrite existing files?", default=False):
            raise SystemExit(1)

    # Download and extract
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tarball = download_package(
            name, version, ver_info["sha256"], tmp_path,
        )

        with tarfile.open(tarball, "r:gz") as tar:
            tar.extractall(tmp_path)

        # Find .agent/ directory inside extracted content
        extracted_agent = None
        for candidate in tmp_path.rglob(AGENT_DIR):
            if candidate.is_dir() and (candidate / "agent.yaml").exists():
                extracted_agent = candidate
                break

        if extracted_agent is None:
            raise click.ClickException(
                f"Downloaded package '{name}@{version}' does not contain "
                f"a {AGENT_DIR}/ directory with agent.yaml"
            )

        # Copy to project root
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
        shutil.copytree(extracted_agent, agent_dir)

    # Auto-sync
    synced_files = run_sync(project_root, force=True, quiet=True)

    console.print()
    console.print(f"[green]Initialized from template:[/] {name}@{version}")
    console.print(f"  Source: {source}")
    console.print(f"  Installed to: {agent_dir}")
    if synced_files > 0:
        console.print(f"  Synced to {synced_files} tool-specific config file(s).")
    console.print()
    console.print("[dim]Done! Start a new agent session to use the template.[/]")


def _init_from_tarball(tarball_path: Path, project_root: Path) -> None:
    """Initialize a project from a local template tarball."""
    agent_dir = project_root / AGENT_DIR

    if agent_dir.exists():
        console.print(f"[yellow]Warning:[/] {AGENT_DIR}/ already exists at {project_root}")
        if not click.confirm("Overwrite existing files?", default=False):
            raise SystemExit(1)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(tmp_path)

        # Find .agent/ directory inside extracted content
        extracted_agent = None
        for candidate in tmp_path.rglob(AGENT_DIR):
            if candidate.is_dir() and (candidate / "agent.yaml").exists():
                extracted_agent = candidate
                break

        if extracted_agent is None:
            raise click.ClickException(
                f"Tarball does not contain a {AGENT_DIR}/ directory with agent.yaml"
            )

        if agent_dir.exists():
            shutil.rmtree(agent_dir)
        shutil.copytree(extracted_agent, agent_dir)

    synced_files = run_sync(project_root, force=True, quiet=True)

    console.print()
    console.print(f"[green]Initialized from template:[/] {tarball_path.name}")
    console.print(f"  Installed to: {agent_dir}")
    if synced_files > 0:
        console.print(f"  Synced to {synced_files} tool-specific config file(s).")
    console.print()
    console.print("[dim]Done! Start a new agent session to use the template.[/]")


@click.command("init")
@click.option("--name", default=None, help="Project name (kebab-case). Default: directory name.")
@click.option("--domain", default="other", help="Project domain (ml, web, devops, etc.). Default: other.")
@click.option("--language", default=None, help="Primary language. Default: auto-detected from files.")
@click.option("--skills/--no-skills", default=True)
@click.option("--workflows/--no-workflows", default=True)
@click.option("--registry/--no-registry", default=False)
@click.option("--path", default=".", type=click.Path(exists=True), help="Project root directory")
@click.option("--from", "from_registry", default=None, help="Initialize from a registry template (e.g. aes-hub/ml-pipeline@^2.0) or local tarball")
def init_cmd(
    name: Optional[str],
    domain: str,
    language: Optional[str],
    skills: bool,
    workflows: bool,
    registry: bool,
    path: str,
    from_registry: Optional[str],
) -> None:
    """Scaffold a .agent/ directory for your project.

    All flags are optional.  Without flags, the project name is derived from
    the directory name, the language is auto-detected from marker files, and
    the domain defaults to a generic scaffold that the LLM fills via /setup.

    Use --from to initialize from a registry template or local tarball.

    \b
    Examples:
      aes init                                     # zero-arg, auto-detect everything
      aes init --name my-app --domain ml           # explicit name and domain
      aes init --language python --no-workflows    # override auto-detect
      aes init --from aes-hub/ml-pipeline@^2.0     # from registry template
      aes init --from ./template.tar.gz            # from local tarball
    """
    project_root = Path(path).resolve()

    # --from: initialize from registry template or local tarball
    if from_registry:
        source_path = Path(from_registry)
        if source_path.exists() and source_path.suffix == ".gz":
            _init_from_tarball(source_path, project_root)
        else:
            _init_from_registry(from_registry, project_root)
        return

    agent_dir = project_root / AGENT_DIR

    # Resolve auto-detect defaults
    if name is None:
        name = _detect_name(project_root)
    if language is None:
        language = _detect_language(project_root)

    if agent_dir.exists():
        console.print(f"[yellow]Warning:[/] {AGENT_DIR}/ already exists at {project_root}")
        if not click.confirm("Overwrite existing files?", default=False):
            raise SystemExit(1)

    # Look up domain config (None for "other" / "data-pipeline")
    domain_config = DOMAIN_CONFIGS.get(domain)

    # Create directory structure
    agent_dir.mkdir(exist_ok=True)
    (agent_dir / MEMORY_DIR).mkdir(exist_ok=True)
    (agent_dir / MEMORY_DIR / "sessions").mkdir(exist_ok=True)
    (agent_dir / OVERRIDES_DIR).mkdir(exist_ok=True)

    if skills:
        (agent_dir / SKILLS_DIR).mkdir(exist_ok=True)
    if workflows:
        (agent_dir / WORKFLOWS_DIR).mkdir(exist_ok=True)
    if registry:
        (agent_dir / REGISTRY_DIR).mkdir(exist_ok=True)

    context = {
        "name": name,
        "domain": domain,
        "language": language,
        "has_skills": skills,
        "has_workflows": workflows,
        "has_registry": registry,
        "domain_config": domain_config,
    }

    # Render templates
    env = Environment(
        loader=FileSystemLoader(str(SCAFFOLD_DIR)),
        keep_trailing_newline=True,
    )

    # agent.yaml
    content = _render_template(env, "agent.yaml.jinja", context)
    (agent_dir / "agent.yaml").write_text(content)

    # instructions.md
    content = _render_template(env, "instructions.md.jinja", context)
    (agent_dir / "instructions.md").write_text(content)

    # permissions.yaml
    content = _render_template(env, "permissions.yaml.jinja", context)
    (agent_dir / "permissions.yaml").write_text(content)

    # .agentignore
    agentignore_path = project_root / AGENTIGNORE_FILE
    if not agentignore_path.exists():
        content = _render_template(env, "agentignore.jinja", context)
        agentignore_path.write_text(content)

    # ORCHESTRATOR.md (if skills enabled)
    if skills:
        content = _render_template(env, "orchestrator.md.jinja", context)
        (agent_dir / SKILLS_DIR / "ORCHESTRATOR.md").write_text(content)

    # Domain-specific skill files (manifest + runbook)
    if skills and domain_config:
        for skill_def in domain_config.skills:
            skill_context = {"skill": skill_def}
            # Skill manifest
            content = _render_template(env, "skill.yaml.jinja", skill_context)
            (agent_dir / SKILLS_DIR / f"{skill_def.id}.skill.yaml").write_text(content)
            # Skill runbook
            content = _render_template(env, "skill.md.jinja", skill_context)
            (agent_dir / SKILLS_DIR / f"{skill_def.id}.md").write_text(content)

    # Domain-specific workflow file
    if workflows and domain_config and domain_config.workflow:
        workflow_context = {"workflow": domain_config.workflow}
        content = _render_template(env, "workflow.yaml.jinja", workflow_context)
        (agent_dir / WORKFLOWS_DIR / f"{domain_config.workflow.id}.yaml").write_text(content)

    # Local config files
    content = _render_template(env, "local.yaml.jinja", context)
    (agent_dir / LOCAL_FILE).write_text(content)

    content = _render_template(env, "local.example.yaml.jinja", context)
    (agent_dir / LOCAL_EXAMPLE_FILE).write_text(content)

    # Memory project.md
    memory_content = f"# {name} — Agent Memory\n\n## Project Overview\n\n## Architecture\n\n## Status\n\n## Key Patterns\n"
    (agent_dir / MEMORY_DIR / "project.md").write_text(memory_content)

    # Commands directory + /setup runbook
    (agent_dir / COMMANDS_DIR).mkdir(exist_ok=True)
    content = _render_template(env, "setup.md.jinja", context)
    (agent_dir / COMMANDS_DIR / "setup.md").write_text(content)

    # Auto-sync: generate tool-specific config files
    synced_files = run_sync(project_root, force=True, quiet=True)

    console.print()
    console.print(f"[green]Initialized AES project:[/] {project_root}")
    console.print()
    console.print(f"  {AGENT_DIR}/")
    console.print(f"    agent.yaml              # Manifest")
    console.print(f"    instructions.md         # Agent instructions")
    console.print(f"    permissions.yaml        # Permissions")
    console.print(f"    local.example.yaml      # Local config template")
    console.print(f"    local.yaml              # Local overrides (gitignored)")
    console.print(f"    commands/               # Agent commands")
    console.print(f"      setup.md              # /setup runbook")
    if skills:
        console.print(f"    skills/                 # Skills")
        console.print(f"      ORCHESTRATOR.md       # Skill sequencing")
        if domain_config:
            for skill_def in domain_config.skills:
                console.print(f"      {skill_def.id}.skill.yaml")
                console.print(f"      {skill_def.id}.md")
    if workflows:
        console.print(f"    workflows/              # State machines")
        if domain_config and domain_config.workflow:
            console.print(f"      {domain_config.workflow.id}.yaml")
    if registry:
        console.print(f"    registry/               # Component registries")
    console.print(f"    memory/                 # Agent memory")
    console.print(f"  .agentignore              # Agent exclusions")
    if synced_files > 0:
        console.print()
        console.print(f"[green]Synced to {synced_files} tool-specific config file(s).[/]")
    console.print()
    console.print("[dim]Done! Start a new agent session, then type /setup to populate your config.[/]")
