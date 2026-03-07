"""aes init — Scaffold a .agent/ directory."""

from __future__ import annotations

import json
import re
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import click
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

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
from aes.commands.install import _safe_extract
from aes.commands.sync import run_sync
from aes.domains import DOMAIN_CONFIGS
from aes.analyzer import analyze_project, ProjectAnalysis
from aes.frameworks import resolve_config

console = Console()

MCP_CONFIG_FILE = ".mcp.json"

_MCP_CONFIG = {
    "mcpServers": {
        "aes-registry": {
            "command": "aes-mcp",
            "args": [],
        }
    }
}


def _write_mcp_config(project_root: Path) -> bool:
    """Write .mcp.json if it doesn't already exist.  Returns True if written."""
    mcp_path = project_root / MCP_CONFIG_FILE
    if mcp_path.exists():
        return False
    mcp_path.write_text(json.dumps(_MCP_CONFIG, indent=2) + "\n")
    return True


# ---------------------------------------------------------------------------
# Auto-detection helpers (kept for backward compat with explicit --language)
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
            _safe_extract(tar, tmp_path)

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
        shutil.copytree(extracted_agent, agent_dir, symlinks=False)

    # Auto-sync
    synced_files = run_sync(project_root, force=True, quiet=True)
    mcp_written = _write_mcp_config(project_root)

    console.print()
    console.print(f"[green]Initialized from template:[/] {name}@{version}")
    console.print(f"  Source: {source}")
    console.print(f"  Installed to: {agent_dir}")
    if synced_files > 0:
        console.print(f"  Synced to {synced_files} tool-specific config file(s).")
    if mcp_written:
        console.print(f"  Created {MCP_CONFIG_FILE} (AES registry MCP server)")
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
            _safe_extract(tar, tmp_path)

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
        shutil.copytree(extracted_agent, agent_dir, symlinks=False)

    synced_files = run_sync(project_root, force=True, quiet=True)
    mcp_written = _write_mcp_config(project_root)

    console.print()
    console.print(f"[green]Initialized from template:[/] {tarball_path.name}")
    console.print(f"  Installed to: {agent_dir}")
    if synced_files > 0:
        console.print(f"  Synced to {synced_files} tool-specific config file(s).")
    if mcp_written:
        console.print(f"  Created {MCP_CONFIG_FILE} (AES registry MCP server)")
    console.print()
    console.print("[dim]Done! Start a new agent session to use the template.[/]")


# ---------------------------------------------------------------------------
# Interactive picker (when nothing detected)
# ---------------------------------------------------------------------------

_PROJECT_TYPE_CHOICES = [
    ("API service", "api"),
    ("Web app", "fullstack"),
    ("CLI tool", "cli-tool"),
    ("Library / Package", "library"),
    ("ML pipeline", "ml"),
    ("DevOps / Infra", "devops"),
    ("Skip", "other"),
]

_LANGUAGE_CHOICES = ["python", "typescript", "javascript", "go", "rust", "java"]

# project_type + language -> list of framework labels (from FRAMEWORK_OVERLAYS keys)
_FRAMEWORK_PICKER: Dict[tuple, List[str]] = {
    ("api", "python"): ["fastapi", "django", "flask"],
    ("api", "typescript"): ["express"],
    ("api", "javascript"): ["express"],
    ("api", "go"): [],  # gin/fiber/echo not in overlays yet
    ("api", "rust"): [],  # actix/rocket/axum not in overlays yet
    ("fullstack", "typescript"): ["nextjs", "react"],
    ("fullstack", "javascript"): ["nextjs", "react"],
    ("web-frontend", "typescript"): ["nextjs", "react"],
    ("web-frontend", "javascript"): ["nextjs", "react"],
}


def _interactive_pick(analysis: ProjectAnalysis) -> tuple:
    """Show an interactive picker when nothing was auto-detected.

    Returns ``(project_type, language, frameworks)`` chosen by the user.
    """
    console.print()
    console.print("[bold]No project files detected.[/] What are you building?\n")

    # --- Project type ---
    for i, (label, _) in enumerate(_PROJECT_TYPE_CHOICES, 1):
        console.print(f"  [bold cyan][{i}][/] {label}")
    console.print()

    type_idx = click.prompt(
        "Choice",
        type=click.IntRange(1, len(_PROJECT_TYPE_CHOICES)),
        default=7,
    )
    chosen_label, chosen_type = _PROJECT_TYPE_CHOICES[type_idx - 1]

    if chosen_type == "other":
        return ("other", analysis.language, [])

    # ML and DevOps use DOMAIN_CONFIGS directly, skip language/framework
    if chosen_type in ("ml", "devops"):
        lang = analysis.language if analysis.language != "other" else "python"
        return (chosen_type, lang, [])

    # --- Language ---
    console.print()
    console.print("[bold]Language?[/]\n")
    for i, lang in enumerate(_LANGUAGE_CHOICES, 1):
        console.print(f"  [bold cyan][{i}][/] {lang.title()}")
    console.print()

    lang_idx = click.prompt(
        "Choice",
        type=click.IntRange(1, len(_LANGUAGE_CHOICES)),
        default=1,
    )
    chosen_lang = _LANGUAGE_CHOICES[lang_idx - 1]

    # --- Framework (optional) ---
    fw_options = _FRAMEWORK_PICKER.get((chosen_type, chosen_lang), [])
    chosen_frameworks: List[str] = []

    if fw_options:
        console.print()
        console.print("[bold]Framework?[/] (optional, Enter to skip)\n")
        for i, fw in enumerate(fw_options, 1):
            console.print(f"  [bold cyan][{i}][/] {fw.title()}")
        console.print(f"  [bold cyan][{len(fw_options) + 1}][/] None")
        console.print()

        fw_idx = click.prompt(
            "Choice",
            type=click.IntRange(1, len(fw_options) + 1),
            default=len(fw_options) + 1,
        )
        if fw_idx <= len(fw_options):
            chosen_frameworks = [fw_options[fw_idx - 1]]

    return (chosen_type, chosen_lang, chosen_frameworks)


def _format_detection_summary(analysis: ProjectAnalysis) -> str:
    """Build a detection summary string for display."""
    lines = []
    lines.append(f"  Language:   [cyan]{analysis.language}[/]")
    if analysis.frameworks:
        fw_str = " + ".join(analysis.frameworks)
        lines.append(f"  Framework:  [cyan]{fw_str}[/]")
    lines.append(f"  Type:       [cyan]{analysis.project_type}[/]")
    if analysis.has_tests:
        cmd_hint = f" ({analysis.test_command})" if analysis.test_command else ""
        lines.append(f"  Tests:      [green]found[/]{cmd_hint}")
    if analysis.has_ci:
        lines.append(f"  CI/CD:      [green]found[/]")
    if analysis.has_docker:
        lines.append(f"  Docker:     [green]found[/]")
    if analysis.has_database:
        lines.append(f"  Database:   [green]migrations found[/]")
    if analysis.existing_agent_configs:
        tools = ", ".join(analysis.existing_agent_configs.keys())
        lines.append(f"  Existing:   [yellow]{tools}[/]")
    return "\n".join(lines)


def _print_post_init_summary(
    project_root: Path,
    name: str,
    project_type: str,
    language: str,
    domain_config: object,
    skills: bool,
    workflows: bool,
    registry: bool,
    synced_files: int,
) -> None:
    """Print a rich post-init summary."""
    from aes.domains import DomainConfig

    # Header
    type_label = project_type.replace("-", " ").title()
    console.print()
    console.print(Panel(
        f"[bold green]AES Initialized:[/] {name}\n"
        f"[dim]{type_label} ({language})[/]",
        expand=False,
    ))

    # File tree
    tree = Tree(f"[bold].agent/[/]")
    tree.add("agent.yaml")
    tree.add(f"instructions.md [dim]({type_label}-specific)[/]")
    tree.add("permissions.yaml")

    if skills:
        skills_branch = tree.add("skills/")
        skills_branch.add("ORCHESTRATOR.md")
        if isinstance(domain_config, DomainConfig):
            for skill_def in domain_config.skills:
                skills_branch.add(f"{skill_def.id} [dim]{skill_def.description}[/]")

    if workflows and isinstance(domain_config, DomainConfig) and domain_config.workflow:
        wf_branch = tree.add("workflows/")
        wf_branch.add(f"{domain_config.workflow.id}.yaml")

    if registry:
        tree.add("registry/")

    tree.add("commands/setup.md")
    tree.add("memory/project.md")

    console.print(tree)

    # Sync summary
    if synced_files > 0:
        console.print()
        console.print(f"[green]Synced to {synced_files} tool config(s):[/]")
        sync_targets = [
            ("Claude Code", "CLAUDE.md"),
            ("Cursor", ".cursorrules"),
            ("Copilot", ".github/copilot-instructions.md"),
            ("Windsurf", ".windsurfrules"),
        ]
        for tool_name, file_name in sync_targets:
            if (project_root / file_name).exists():
                console.print(f"  {tool_name:12s} -> {file_name}")

    # MCP info
    mcp_path = project_root / MCP_CONFIG_FILE
    if mcp_path.exists():
        console.print()
        console.print(f"[green]MCP:[/] {MCP_CONFIG_FILE} configured (AES registry tools)")
        console.print("  [dim]Install MCP server: pip install aes-cli[mcp][/]")

    # Next steps
    console.print()
    console.print("[dim]Next: Start a new agent session, then type /setup to fine-tune.[/]")


@click.command("init")
@click.option("--name", default=None, help="Project name (kebab-case). Default: directory name.")
@click.option("--domain", default=None, help="Project domain (ml, web, devops, etc.). Default: auto-detected.")
@click.option("--language", default=None, help="Primary language. Default: auto-detected from files.")
@click.option("--skills/--no-skills", default=True)
@click.option("--workflows/--no-workflows", default=True)
@click.option("--registry/--no-registry", default=False)
@click.option("--path", default=".", type=click.Path(exists=True), help="Project root directory")
@click.option("--from", "from_registry", default=None, help="Initialize from a registry template (e.g. aes-hub/ml-pipeline@^2.0) or local tarball")
def init_cmd(
    name: Optional[str],
    domain: Optional[str],
    language: Optional[str],
    skills: bool,
    workflows: bool,
    registry: bool,
    path: str,
    from_registry: Optional[str],
) -> None:
    """Scaffold a .agent/ directory for your project.

    All flags are optional.  Without flags, the project is analyzed to detect
    language, frameworks, and project type.  The generated .agent/ is tailored
    to the detected stack.

    Use --domain ml/web/devops to use a pre-built domain config instead of
    auto-detection.  Use --from for registry templates or local tarballs.

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

    # --- Smart detection mode ---
    # When no --domain is given, analyze the project
    analysis: Optional[ProjectAnalysis] = None
    detected_domain_config = None

    if domain is None:
        analysis = analyze_project(project_root)

        # Use analysis for defaults
        if name is None:
            name = analysis.name
        if language is None:
            language = analysis.language

        # Try to resolve a framework-aware config
        detected_domain_config = resolve_config(
            project_type=analysis.project_type,
            frameworks=analysis.frameworks,
            language=language,
            test_command=analysis.test_command,
            build_command=analysis.build_command,
        )

        # Interactive mode: show what we found and confirm
        is_interactive = sys.stdin.isatty() and not any(
            x in sys.argv for x in ("--name", "--language")
        )
        if is_interactive and (analysis.frameworks or analysis.project_type != "other"):
            console.print()
            console.print(Panel(
                f"[bold]Detected:[/]\n{_format_detection_summary(analysis)}",
                title="Project Analysis",
                expand=False,
            ))

            type_label = analysis.project_type.replace("-", " ").title()
            fw_str = ""
            if analysis.frameworks:
                fw_str = " + ".join(f.title() for f in analysis.frameworks) + " "
            if not click.confirm(
                f"\nGenerate .agent/ for {fw_str}{type_label}?",
                default=True,
            ):
                raise SystemExit(0)

            # Offer to import existing agent configs
            if analysis.existing_agent_configs:
                console.print()
                for tool, cfg_path in analysis.existing_agent_configs.items():
                    size = cfg_path.stat().st_size
                    console.print(f"  Found existing: [yellow]{cfg_path.name}[/] ({size / 1024:.1f} KB)")

        elif is_interactive:
            # Nothing detected — show interactive picker
            picked_type, picked_lang, picked_frameworks = _interactive_pick(analysis)

            language = picked_lang
            if picked_type in ("ml", "devops"):
                detected_domain_config = DOMAIN_CONFIGS.get(picked_type)
            elif picked_type != "other":
                detected_domain_config = resolve_config(
                    project_type=picked_type,
                    frameworks=picked_frameworks,
                    language=picked_lang,
                )
            # Update analysis so post-init summary is correct
            analysis = ProjectAnalysis(
                name=analysis.name,
                language=picked_lang,
                frameworks=picked_frameworks,
                project_type=picked_type,
            )

        # Fall into "other" domain handling for the template context
        domain = analysis.project_type if detected_domain_config else "other"
    else:
        # Explicit --domain: use legacy behavior
        if name is None:
            name = _detect_name(project_root)
        if language is None:
            language = _detect_language(project_root)

    if agent_dir.exists():
        console.print(f"[yellow]Warning:[/] {AGENT_DIR}/ already exists at {project_root}")
        if not click.confirm("Overwrite existing files?", default=False):
            raise SystemExit(1)

    # Look up domain config: framework-resolved > explicit domain > None
    domain_config = detected_domain_config or DOMAIN_CONFIGS.get(domain)

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
    _write_mcp_config(project_root)

    # Determine project type label for output
    project_type = "other"
    if analysis is not None:
        project_type = analysis.project_type
    elif domain in ("ml", "web", "devops"):
        project_type = domain

    _print_post_init_summary(
        project_root=project_root,
        name=name,
        project_type=project_type,
        language=language,
        domain_config=domain_config,
        skills=skills,
        workflows=workflows,
        registry=registry,
        synced_files=synced_files,
    )
