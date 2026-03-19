"""aes sync — Generate tool-specific config files from .agent/ directory."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import yaml
from rich.console import Console

from aes.config import (
    AGENT_DIR,
    COMMANDS_DIR,
    INSTINCTS_DIR,
    LEARNING_CONFIG_FILE,
    LIFECYCLE_FILE,
    LOCAL_FILE,
    MANIFEST_FILE,
    MEMORY_DIR,
    PERMISSIONS_FILE,
    RULES_CONFIG_FILE,
    RULES_DIR,
    SKILLS_DIR,
)
from aes.i18n import t
from aes.targets import TARGETS, TARGET_NAMES, AgentContext, SyncPlan

console = Console()

SYNC_MANIFEST = ".aes-sync.json"


def _validate_subpath(base: Path, child: Path) -> None:
    """Ensure *child* resolves to a location under *base*.

    Raises click.ClickException on path traversal attempts.
    """
    try:
        child.resolve().relative_to(base.resolve())
    except ValueError:
        raise click.ClickException(
            f"Path traversal blocked: {child} escapes {base}"
        )


def run_sync(
    project_root: Path,
    target_names: Optional[List[str]] = None,
    force: bool = False,
    quiet: bool = False,
) -> int:
    """Run sync programmatically. Returns number of files written.

    Used by ``aes init`` to auto-sync after scaffolding.
    """
    agent_dir = project_root / AGENT_DIR

    if not agent_dir.exists() or not (agent_dir / MANIFEST_FILE).exists():
        return 0

    ctx = _load_agent_context(project_root)
    selected = target_names or TARGET_NAMES

    all_plans: List[SyncPlan] = []
    for name in selected:
        adapter = TARGETS[name]()
        try:
            all_plans.append(adapter.plan(ctx, force))
        except click.ClickException:
            # Target-specific validation failure — skip when syncing
            # multiple targets (e.g. openclaw requires identity/model
            # which non-assistant projects won't have).
            if len(selected) == 1:
                raise
            continue

    sync_manifest = _load_sync_manifest(project_root)
    written = 0

    for sync_plan in all_plans:
        for gf in sync_plan.files:
            if gf.action in ("create", "update"):
                full_path = project_root / gf.relative_path
                _validate_subpath(project_root, full_path)
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(gf.content)
                sync_manifest["files"][gf.relative_path] = {
                    "target": sync_plan.target_name,
                    "sha256": _sha256(gf.content),
                }
                written += 1

    if written > 0:
        sync_manifest["synced_at"] = datetime.now(timezone.utc).isoformat()
        _save_sync_manifest(project_root, sync_manifest)

    return written


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge *override* into *base*.

    Lists are extended (not replaced).  Scalars from *override* win.
    Returns a new dict — neither input is mutated.
    """
    merged = dict(base)
    for key, val in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = _deep_merge(merged[key], val)
        elif key in merged and isinstance(merged[key], list) and isinstance(val, list):
            merged[key] = merged[key] + val
        else:
            merged[key] = val
    return merged


def _load_agent_context(project_root: Path) -> AgentContext:
    """Load all .agent/ contents into an AgentContext."""
    agent_dir = project_root / AGENT_DIR

    # Load manifest
    with open(agent_dir / MANIFEST_FILE) as f:
        manifest = yaml.safe_load(f) or {}

    agent_section = manifest.get("agent", {})

    # Load instructions
    instructions: Optional[str] = None
    instructions_rel = agent_section.get("instructions", "instructions.md")
    instructions_path = agent_dir / instructions_rel
    _validate_subpath(agent_dir, instructions_path)
    if instructions_path.exists():
        instructions = instructions_path.read_text()

    # Load orchestrator
    orchestrator: Optional[str] = None
    orchestrator_rel = agent_section.get("orchestrator")
    if orchestrator_rel:
        orchestrator_path = agent_dir / orchestrator_rel
        _validate_subpath(agent_dir, orchestrator_path)
        if orchestrator_path.exists():
            orchestrator = orchestrator_path.read_text()

    # Load skill runbooks and metadata in manifest order
    skill_runbooks: Dict[str, str] = {}
    skill_metadata: Dict[str, Dict[str, Any]] = {}
    for skill_ref in manifest.get("skills", []):
        skill_id = skill_ref.get("id", "unknown")
        runbook_rel = skill_ref.get("runbook")
        if runbook_rel:
            runbook_path = agent_dir / runbook_rel
            _validate_subpath(agent_dir, runbook_path)
            if runbook_path.exists():
                skill_runbooks[skill_id] = runbook_path.read_text()
        # Load skill manifest for name/description/activation metadata
        manifest_rel = skill_ref.get("manifest")
        if manifest_rel:
            skill_manifest_path = agent_dir / manifest_rel
            _validate_subpath(agent_dir, skill_manifest_path)
            if skill_manifest_path.exists():
                with open(skill_manifest_path) as f:
                    skill_data = yaml.safe_load(f) or {}
                skill_metadata[skill_id] = {
                    "name": skill_data.get("name", skill_id),
                    "description": skill_data.get("description", ""),
                    "negative_triggers": skill_data.get("negative_triggers", []),
                    "activation": skill_data.get("activation", "explicit"),
                    "allowed_tools": skill_data.get("allowed_tools"),
                    "version": skill_data.get("version", "0.1.0"),
                    "emoji": skill_data.get("emoji", ""),
                    "license": skill_data.get("license", "MIT"),
                    "user_invocable": skill_data.get("user_invocable", True),
                    "primary_env": skill_data.get("primary_env", ""),
                    "requires_bins": (skill_data.get("requires") or {}).get("bins", []),
                    "requires_env": (skill_data.get("requires") or {}).get("env", []),
                    "mcp_server": skill_data.get("mcp_server"),
                }
        if skill_id not in skill_metadata:
            skill_metadata[skill_id] = {
                "name": skill_id,
                "description": "",
                "negative_triggers": [],
                "activation": "explicit",
                "allowed_tools": None,
            }

    # Load permissions
    permissions: Optional[dict] = None
    permissions_rel = agent_section.get("permissions", PERMISSIONS_FILE)
    permissions_path = agent_dir / permissions_rel
    _validate_subpath(agent_dir, permissions_path)
    if permissions_path.exists():
        with open(permissions_path) as f:
            permissions = yaml.safe_load(f) or {}

    # Load commands with file content
    commands: List[dict] = []
    for cmd_ref in manifest.get("commands", []):
        cmd_data = dict(cmd_ref)
        cmd_path = agent_dir / cmd_ref["path"]
        _validate_subpath(agent_dir, cmd_path)
        if cmd_path.exists():
            cmd_data["content"] = cmd_path.read_text()
        else:
            cmd_data["content"] = (
                f"# Command: /{cmd_ref.get('id', '?')}\n\nCommand file not found.\n"
            )
        commands.append(cmd_data)

    # Load memory/project.md
    memory_project: Optional[str] = None
    memory_path = agent_dir / MEMORY_DIR / "project.md"
    if memory_path.exists():
        memory_project = memory_path.read_text()

    # Load local.yaml and deep-merge permissions
    local_config: Optional[dict] = None
    local_path = agent_dir / LOCAL_FILE
    if local_path.exists():
        with open(local_path) as f:
            local_config = yaml.safe_load(f) or {}
        # Merge local permissions on top of shared permissions
        local_perms = local_config.get("permissions")
        if local_perms and permissions:
            permissions = _deep_merge(permissions, local_perms)

    # Load lifecycle.yaml
    lifecycle: Optional[dict] = None
    lifecycle_path = agent_dir / LIFECYCLE_FILE
    if lifecycle_path.exists():
        with open(lifecycle_path) as f:
            lifecycle = yaml.safe_load(f) or {}

    # Load learning config and active instincts
    learning_config: Optional[dict] = None
    active_instincts: List[dict] = []
    learning_config_path = agent_dir / LEARNING_CONFIG_FILE
    if learning_config_path.exists():
        with open(learning_config_path) as f:
            learning_config = yaml.safe_load(f) or {}

    instincts_active_dir = agent_dir / INSTINCTS_DIR / "active"
    if instincts_active_dir.exists():
        max_instincts = 10
        if learning_config:
            max_instincts = (
                learning_config.get("context_loading", {})
                .get("max_instincts_in_context", 10)
            )
        raw_instincts = []
        for inst_file in sorted(instincts_active_dir.glob("*.instinct.yaml")):
            with open(inst_file) as f:
                inst_data = yaml.safe_load(f)
            if inst_data:
                raw_instincts.append(inst_data)
        # Sort by confidence score descending
        raw_instincts.sort(
            key=lambda i: i.get("confidence", {}).get("score", 0),
            reverse=True,
        )
        active_instincts = raw_instincts[:max_instincts]

    # Load rules config and rule files
    rules_config: Optional[dict] = None
    rules_files: Dict[str, str] = {}
    rules_config_path = agent_dir / RULES_CONFIG_FILE
    if rules_config_path.exists():
        with open(rules_config_path) as f:
            rules_config = yaml.safe_load(f) or {}

        rules_base = agent_dir / RULES_DIR
        overrides = rules_config.get("overrides", {})

        # Determine which language directories to load
        languages = rules_config.get("languages", [])
        if not languages:
            # Auto-detect from project root
            detection = rules_config.get("detection", {})
            for lang, patterns in detection.items():
                for pattern in patterns:
                    if list(project_root.glob(pattern)):
                        languages.append(lang)
                        break

        # Always-load directories (default: common)
        always = rules_config.get("loading", {}).get("always", ["common"])
        dirs_to_load = list(always) + languages

        for dir_name in dirs_to_load:
            rule_dir = rules_base / dir_name
            if not rule_dir.exists():
                continue
            for md_file in sorted(rule_dir.glob("*.md")):
                content = md_file.read_text()
                # Resolve ${variable} placeholders from overrides
                rule_name = md_file.stem
                rule_overrides = overrides.get(rule_name, {})
                for var_name, var_value in rule_overrides.items():
                    content = content.replace(
                        f"${{{var_name}}}", str(var_value)
                    )
                key = f"{dir_name}/{md_file.name}"
                rules_files[key] = content

    return AgentContext(
        project_root=project_root,
        agent_dir=agent_dir,
        manifest=manifest,
        instructions=instructions,
        orchestrator=orchestrator,
        skill_runbooks=skill_runbooks,
        permissions=permissions,
        commands=commands,
        memory_project=memory_project,
        skill_metadata=skill_metadata,
        local_config=local_config,
        lifecycle=lifecycle,
        learning_config=learning_config,
        active_instincts=active_instincts,
        rules_config=rules_config,
        rules_files=rules_files,
    )


def _load_sync_manifest(project_root: Path) -> dict:
    """Load .aes-sync.json if it exists."""
    path = project_root / SYNC_MANIFEST
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"files": {}, "synced_at": None}


def _save_sync_manifest(project_root: Path, data: dict) -> None:
    """Save .aes-sync.json."""
    path = project_root / SYNC_MANIFEST
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


@click.command("sync")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option(
    "--target",
    "-t",
    multiple=True,
    type=click.Choice(TARGET_NAMES, case_sensitive=False),
    help="Target tool(s) to sync. Repeatable. Default: all.",
)
@click.option("--dry-run", is_flag=True, help="Show what would be generated without writing.")
@click.option("--force", is_flag=True, help="Overwrite files not generated by aes sync.")
@click.option("--clean", is_flag=True, help="Remove previously synced files.")
def sync_cmd(
    path: str,
    target: tuple,  # type: ignore[type-arg]
    dry_run: bool,
    force: bool,
    clean: bool,
) -> None:
    """Generate tool-specific config files from .agent/ directory.

    Reads .agent/ and generates configuration files for AI coding tools
    (Claude Code, Cursor, Copilot, Windsurf).

    PATH is the project root directory (default: current directory).
    """
    project_root = Path(path).resolve()
    agent_dir = project_root / AGENT_DIR

    if not agent_dir.exists():
        console.print(f"[red]{t('common.error')}:[/] {t('common.no_agent_dir', agent_dir=AGENT_DIR, path=project_root)}")
        console.print(f"[dim]{t('common.run_init_hint')}[/]")
        raise SystemExit(1)

    if not (agent_dir / MANIFEST_FILE).exists():
        console.print(f"[red]{t('common.error')}:[/] {t('common.no_manifest', manifest=MANIFEST_FILE, agent_dir=agent_dir)}")
        raise SystemExit(1)

    # Handle --clean
    if clean:
        _do_clean(project_root, dry_run)
        return

    # Load context
    ctx = _load_agent_context(project_root)

    # Select targets
    if target:
        selected = list(target)
    elif sys.stdin.isatty():
        selected = _prompt_target_selection()
    else:
        selected = list(TARGET_NAMES)
    console.print(f"[bold]{t('sync.syncing')}[/] {project_root}")
    console.print(f"  {t('sync.targets', targets=', '.join(selected))}")
    console.print()

    # Generate plans
    all_plans: List[SyncPlan] = []
    for target_name in selected:
        adapter = TARGETS[target_name]()
        try:
            sync_plan = adapter.plan(ctx, force)
        except click.ClickException as exc:
            # Target-specific validation failure (e.g. openclaw requires
            # identity/model). When syncing a single explicit target, re-raise
            # so the user sees the error. When syncing all targets, skip and
            # warn — not every project is compatible with every target.
            if len(selected) == 1:
                raise
            console.print(
                f"  [yellow]⚠ {target_name}:[/] {exc.format_message()}"
            )
            continue
        all_plans.append(sync_plan)

    # Execute plans
    sync_manifest = _load_sync_manifest(project_root)
    created = 0
    updated = 0
    conflicts = 0

    for sync_plan in all_plans:
        if sync_plan.files:
            console.print(f"[bold cyan]{sync_plan.target_name}[/]")

        for gf in sync_plan.files:
            if gf.action == "create":
                icon = "[green]+[/]"
                created += 1
            elif gf.action == "update":
                icon = "[yellow]~[/]"
                updated += 1
            else:
                icon = "[red]![/]"
                conflicts += 1

            console.print(f"  {icon} {gf.relative_path}  [dim]({gf.description})[/]")

            if gf.action == "conflict":
                console.print(
                    f"    [red]{t('sync.conflict_exists')}[/]"
                )
                console.print(f"    [dim]{t('sync.use_force')}[/]")
                continue

            if gf.action in ("create", "update") and not dry_run:
                full_path = project_root / gf.relative_path
                _validate_subpath(project_root, full_path)
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(gf.content)
                sync_manifest["files"][gf.relative_path] = {
                    "target": sync_plan.target_name,
                    "sha256": _sha256(gf.content),
                }

        for warning in sync_plan.warnings:
            console.print(f"  [yellow]{t('common.warning')}:[/] {warning}")

        if sync_plan.files:
            console.print()

    # Save manifest
    if not dry_run and (created + updated > 0):
        sync_manifest["synced_at"] = datetime.now(timezone.utc).isoformat()
        _save_sync_manifest(project_root, sync_manifest)

    # Summary
    if dry_run:
        console.print(f"[dim]{t('sync.dry_run')}[/]")
    console.print(
        f"[bold]{t('common.summary')}:[/] {t('sync.sync_summary', created=created, updated=updated, conflicts=conflicts)}"
    )

    if conflicts > 0:
        raise SystemExit(1)


def _do_clean(project_root: Path, dry_run: bool) -> None:
    """Remove all previously synced files."""
    sync_manifest = _load_sync_manifest(project_root)
    files = sync_manifest.get("files", {})

    if not files:
        console.print(f"[dim]{t('sync.no_synced_files')}[/]")
        return

    removed = 0
    for rel_path in list(files.keys()):
        full_path = project_root / rel_path
        if full_path.exists():
            console.print(f"  [red]-[/] {rel_path}")
            if not dry_run:
                full_path.unlink()
                removed += 1
        else:
            console.print(f"  [dim]-[/] {rel_path} [dim]({t('sync.already_gone')})[/]")

    if not dry_run:
        _save_sync_manifest(project_root, {"files": {}, "synced_at": None})

    if dry_run:
        console.print(f"[dim]{t('sync.dry_run_remove', count=len(files))}[/]")
    else:
        console.print(f"[green]{t('sync.cleaned', count=removed)}[/]")


def _prompt_target_selection() -> List[str]:
    """Interactively prompt the user to select sync target(s)."""
    console.print(f"[bold]{t('sync.select_targets')}[/]\n")
    for i, name in enumerate(TARGET_NAMES, 1):
        console.print(f"  [bold cyan][{i}][/] {name}")
    all_idx = len(TARGET_NAMES) + 1
    console.print(f"  [bold cyan][{all_idx}][/] {t('sync.all')}")
    console.print()

    raw = click.prompt(
        t("sync.choice_prompt"),
        type=str,
        default=str(all_idx),
    )

    choices = [c.strip() for c in raw.split(",")]
    selected: List[str] = []
    for c in choices:
        try:
            idx = int(c)
        except ValueError:
            if c.lower() in TARGET_NAMES:
                selected.append(c.lower())
            continue
        if idx == all_idx:
            return list(TARGET_NAMES)
        if 1 <= idx <= len(TARGET_NAMES):
            selected.append(TARGET_NAMES[idx - 1])

    if not selected:
        console.print(f"[yellow]{t('sync.no_valid_selection')}[/]")
        return list(TARGET_NAMES)

    return selected
