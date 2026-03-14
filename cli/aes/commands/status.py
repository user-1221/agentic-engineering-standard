"""aes status — Show sync status: what changed since last sync."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console

from aes.config import AGENT_DIR, MANIFEST_FILE
from aes.i18n import t
from aes.targets import TARGETS, TARGET_NAMES, AgentContext, SyncPlan

console = Console()

SYNC_MANIFEST = ".aes-sync.json"


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _load_sync_manifest(project_root: Path) -> dict:
    path = project_root / SYNC_MANIFEST
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"files": {}, "synced_at": None}


@click.command("status")
@click.argument("path", default=".", type=click.Path(exists=True))
def status_cmd(path: str) -> None:
    """Show sync status — what changed since last sync.

    Re-generates tool configs in memory and compares against the stored
    hashes from the last ``aes sync`` run.

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

    sync_manifest = _load_sync_manifest(project_root)
    synced_at = sync_manifest.get("synced_at")
    tracked_files = sync_manifest.get("files", {})

    if not synced_at:
        console.print(f"[yellow]{t('status.no_sync_history')}[/]")
        console.print(f"[dim]{t('status.run_sync_hint')}[/]")
        return

    # Re-generate all plans in memory
    from aes.commands.sync import _load_agent_context  # noqa: avoid circular at top

    ctx = _load_agent_context(project_root)
    would_generate: dict = {}  # rel_path -> content

    for name in TARGET_NAMES:
        adapter = TARGETS[name]()
        plan = adapter.plan(ctx, force=True)
        for gf in plan.files:
            would_generate[gf.relative_path] = gf.content

    # Compare
    modified_sources: List[str] = []  # .agent/ changed → sync stale
    output_status: List[tuple] = []  # (rel_path, status_str)
    missing_outputs: List[str] = []
    untracked_would: List[str] = []

    for rel_path, info in tracked_files.items():
        stored_hash = info.get("sha256", "")
        full_path = project_root / rel_path

        if not full_path.exists():
            missing_outputs.append(rel_path)
            continue

        on_disk_hash = _sha256(full_path.read_text())

        if rel_path in would_generate:
            would_hash = _sha256(would_generate[rel_path])
            if would_hash != stored_hash:
                # Source .agent/ changed → sync would produce different output
                modified_sources.append(rel_path)
            elif on_disk_hash != stored_hash:
                # Output was hand-edited after sync
                output_status.append((rel_path, t("status.manually_edited")))
            else:
                output_status.append((rel_path, t("status.up_to_date")))
        else:
            # Tracked file no longer generated (target removed?)
            if on_disk_hash == stored_hash:
                output_status.append((rel_path, t("status.target_removed")))
            else:
                output_status.append((rel_path, t("status.manually_edited")))

    # Files that would be generated but aren't tracked yet
    for rel_path in would_generate:
        if rel_path not in tracked_files:
            untracked_would.append(rel_path)

    # Print report
    console.print(f"[bold]{t('status.title')}[/]  ({t('status.last_synced', time=synced_at)})")
    console.print()

    needs_sync = False

    if modified_sources:
        needs_sync = True
        console.print(f"  [yellow]{t('status.source_changed')}[/]")
        for rp in modified_sources:
            console.print(f"    [yellow]~[/] {rp}")
        console.print()

    if missing_outputs:
        needs_sync = True
        console.print(f"  [red]{t('status.missing_outputs')}[/]")
        for rp in missing_outputs:
            console.print(f"    [red]-[/] {rp}")
        console.print()

    if untracked_would:
        needs_sync = True
        console.print(f"  [yellow]{t('status.new_outputs')}[/]")
        for rp in untracked_would:
            console.print(f"    [green]+[/] {rp}")
        console.print()

    if output_status:
        console.print(f"  [dim]{t('status.synced_outputs')}[/]")
        for rp, status in output_status:
            if status == t("status.up_to_date"):
                console.print(f"    [green]=[/] {rp}  [dim]({status})[/]")
            else:
                console.print(f"    [yellow]![/] {rp}  [dim]({status})[/]")
        console.print()

    if needs_sync:
        console.print(f"[yellow]{t('status.action_sync')}[/]")
    else:
        console.print(f"[green]{t('status.everything_up_to_date')}[/]")
