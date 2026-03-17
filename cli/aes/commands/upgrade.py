"""aes upgrade — Upgrade .agent/ to the current AES spec version."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import click
import yaml
from jinja2 import ChoiceLoader, Environment, FileSystemLoader
from rich.console import Console

from aes.config import AGENT_DIR, COMMANDS_DIR, MANIFEST_FILE, SCAFFOLD_DIR
from aes.i18n import t
from aes.migrations import (
    CURRENT_SPEC_VERSION,
    Migration,
    MigrationFile,
    applicable_migrations,
)

console = Console()


# ---------------------------------------------------------------------------
# Upgrade plan data structures
# ---------------------------------------------------------------------------


@dataclass
class PlannedFile:
    """A file to create during upgrade."""

    migration_file: MigrationFile
    create_file: bool  # whether the file needs creating
    add_manifest_entry: bool  # whether the manifest entry needs adding


@dataclass
class UpgradePlan:
    """The full upgrade plan."""

    current_version: str
    target_version: str
    migrations: List[Migration] = field(default_factory=list)
    planned_files: List[PlannedFile] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.planned_files) or self.current_version != self.target_version


# ---------------------------------------------------------------------------
# Plan computation
# ---------------------------------------------------------------------------


def _compute_plan(agent_dir: Path, manifest: dict) -> UpgradePlan:
    """Compare current .agent/ against migrations to determine needed changes."""
    current_version = manifest.get("aes", "1.0")
    migrations = applicable_migrations(current_version)

    plan = UpgradePlan(
        current_version=current_version,
        target_version=CURRENT_SPEC_VERSION,
        migrations=migrations,
    )

    for migration in migrations:
        for mf in migration.files:
            file_path = agent_dir / mf.relative_path
            file_exists = file_path.exists()

            entry_exists = False
            if mf.manifest_entry and mf.manifest_section:
                entry_id = mf.manifest_entry.get("id", "")
                section = manifest.get(mf.manifest_section, [])
                entry_exists = any(
                    item.get("id") == entry_id for item in section
                )

            needs_file = not file_exists
            needs_entry = bool(mf.manifest_entry) and not entry_exists

            if needs_file or needs_entry:
                plan.planned_files.append(
                    PlannedFile(
                        migration_file=mf,
                        create_file=needs_file,
                        add_manifest_entry=needs_entry,
                    )
                )

    return plan


# ---------------------------------------------------------------------------
# Plan display
# ---------------------------------------------------------------------------


def _display_plan(plan: UpgradePlan) -> None:
    """Display the upgrade plan without applying it."""
    console.print()
    console.print(f"[bold]{t('upgrade.title')}[/]")
    console.print()
    console.print(
        f"  {t('upgrade.current_version', version=plan.current_version)}"
    )
    console.print(
        f"  {t('upgrade.target_version', version=plan.target_version)}"
    )
    console.print()

    for migration in plan.migrations:
        console.print(
            f"  [bold cyan]{t('upgrade.migration_header', from_v=migration.from_version, to_v=migration.to_version, description=migration.description)}[/]"
        )

    for pf in plan.planned_files:
        mf = pf.migration_file
        if pf.create_file:
            console.print(
                f"    [green]+[/] {mf.relative_path}  [dim]({t('upgrade.new_file')})[/]"
            )
        if pf.add_manifest_entry and mf.manifest_entry:
            entry_id = mf.manifest_entry.get("id", "?")
            console.print(
                f"    [green]+[/] agent.yaml: {mf.manifest_section}[]  [dim]({t('upgrade.add_entry', id=entry_id)})[/]"
            )

    if plan.current_version != plan.target_version:
        console.print(
            f"    [yellow]~[/] agent.yaml: aes  [dim]({t('upgrade.bump_version', old=plan.current_version, new=plan.target_version)})[/]"
        )

    console.print()
    console.print(f"  [dim]{t('upgrade.run_apply')}[/]")


# ---------------------------------------------------------------------------
# Apply logic
# ---------------------------------------------------------------------------


def _apply_plan(
    agent_dir: Path,
    manifest: dict,
    plan: UpgradePlan,
    env: Environment,
    context: dict,
) -> int:
    """Apply the upgrade plan. Returns number of files created."""
    created = 0

    for pf in plan.planned_files:
        mf = pf.migration_file

        # Create missing file from template
        if pf.create_file:
            tmpl = env.get_template(mf.template_name)
            content = tmpl.render(**context)
            file_path = agent_dir / mf.relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            console.print(
                f"  [green]+[/] {t('upgrade.created_file', path=mf.relative_path)}"
            )
            created += 1

        # Add manifest entry
        if pf.add_manifest_entry and mf.manifest_entry:
            section = manifest.setdefault(mf.manifest_section, [])
            section.append(dict(mf.manifest_entry))

    # Bump aes version
    if plan.current_version != plan.target_version:
        manifest["aes"] = plan.target_version

    # Write updated agent.yaml
    yaml_path = agent_dir / MANIFEST_FILE
    with open(yaml_path, "w") as f:
        yaml.safe_dump(
            manifest,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    console.print(
        f"  [yellow]~[/] {t('upgrade.updated_manifest', old=plan.current_version, new=plan.target_version)}"
    )

    return created


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


@click.command("upgrade")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--apply", "do_apply", is_flag=True, help="Apply the upgrade (default: dry-run).")
def upgrade_cmd(path: str, do_apply: bool) -> None:
    """Upgrade .agent/ to the current AES spec version.

    Adds missing files and manifest entries introduced in newer versions
    without touching existing customizations.

    Without --apply, shows what would change (dry-run).

    \b
    Examples:
      aes upgrade                    # show upgrade plan
      aes upgrade --apply            # apply and auto-sync
      aes upgrade /path/to/project   # target a specific project
    """
    project_root = Path(path).resolve()
    agent_dir = project_root / AGENT_DIR

    if not agent_dir.exists() or not (agent_dir / MANIFEST_FILE).exists():
        console.print(
            f"[red]{t('common.error')}:[/] {t('upgrade.no_agent_dir')}"
        )
        console.print(f"[dim]{t('common.run_init_hint')}[/]")
        raise SystemExit(1)

    # Load manifest
    with open(agent_dir / MANIFEST_FILE) as f:
        manifest = yaml.safe_load(f) or {}

    # Compute plan
    plan = _compute_plan(agent_dir, manifest)

    if not plan.has_changes:
        console.print(
            f"\n  {t('upgrade.up_to_date', version=plan.target_version)}\n"
        )
        return

    if not do_apply:
        _display_plan(plan)
        return

    # Build Jinja2 environment (locale-aware, same as init.py)
    from aes.i18n import get_current_locale

    locale = get_current_locale()
    loaders = []
    if locale != "en":
        locale_dir = SCAFFOLD_DIR / locale
        if locale_dir.exists():
            loaders.append(FileSystemLoader(str(locale_dir)))
    loaders.append(FileSystemLoader(str(SCAFFOLD_DIR)))

    env = Environment(
        loader=ChoiceLoader(loaders),
        keep_trailing_newline=True,
    )

    # Template context — minimal, just what the templates need
    context = {
        "name": manifest.get("name", "project"),
        "domain": manifest.get("domain", "other"),
        "language": manifest.get("runtime", {}).get("language", "other"),
    }

    console.print()
    created = _apply_plan(agent_dir, manifest, plan, env, context)

    # Auto-sync
    from aes.commands.sync import run_sync

    synced = run_sync(project_root, force=True, quiet=True)
    if synced > 0:
        console.print(f"  [green]{t('upgrade.synced', count=synced)}[/]")

    console.print(
        f"\n  [bold green]{t('upgrade.applied', count=created)}[/]\n"
    )
