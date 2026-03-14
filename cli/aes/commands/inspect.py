"""aes inspect — Show project structure and stats."""

from __future__ import annotations

import tarfile
import tempfile
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.table import Table

from aes.config import AGENT_DIR
from aes.registry import (
    fetch_index,
    download_package,
    parse_registry_source,
    resolve_version,
    _parse_version,
)
from aes.commands.install import _safe_extract

console = Console()


def _load_yaml(path: Path) -> dict:
    """Load YAML file, return empty dict on error."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _render_workflow_diagram(workflow: dict) -> str:
    """Render a simple ASCII state diagram from a workflow definition."""
    states = workflow.get("states", {})
    transitions = workflow.get("transitions", [])

    if not states or not transitions:
        return "  (no states or transitions defined)"

    lines = []
    # Find initial and terminal states
    initial = [s for s, v in states.items() if v.get("initial")]
    terminal = [s for s, v in states.items() if v.get("terminal")]
    intermediate = [s for s in states if s not in initial and s not in terminal]

    # Render flow
    all_ordered = initial + intermediate + terminal
    if all_ordered:
        # Build transition map
        tx_map: dict[str, list[str]] = {}
        for tx in transitions:
            src = tx.get("from", "")
            dst = tx.get("to", "")
            tx_map.setdefault(src, []).append(dst)

        # Show forward transitions
        forward_chain = initial.copy()
        visited = set(initial)
        current = initial[0] if initial else ""
        while current:
            targets = tx_map.get(current, [])
            next_state = None
            for t in targets:
                if t not in visited and t not in terminal:
                    next_state = t
                    break
            if next_state:
                forward_chain.append(next_state)
                visited.add(next_state)
                current = next_state
            else:
                break

        lines.append("  " + " --> ".join(forward_chain))
        if terminal:
            lines.append("  Terminal: " + ", ".join(terminal))

        # Show backward transitions
        backward = [tx for tx in transitions if tx.get("to") in visited and
                     all_ordered.index(tx.get("from", "")) > all_ordered.index(tx.get("to", ""))
                     if tx.get("from", "") in all_ordered and tx.get("to", "") in all_ordered]
        for tx in backward:
            lines.append(f"  (loop) {tx['from']} --> {tx['to']}: {tx.get('description', 'reframe')}")

    return "\n".join(lines) if lines else "  (could not render diagram)"


def _is_local_path(target: str) -> bool:
    """Return True if target looks like a local filesystem path."""
    if target.startswith(("/", "./", "../")):
        return True
    if Path(target).is_dir():
        return True
    return False


def _inspect_local(path: str) -> None:
    """Inspect a local .agent/ directory."""
    project_root = Path(path).resolve()
    agent_dir = project_root / AGENT_DIR

    if not agent_dir.exists():
        console.print(f"[red]Error:[/] No {AGENT_DIR}/ directory found at {project_root}")
        raise SystemExit(1)

    manifest_path = agent_dir / "agent.yaml"
    if not manifest_path.exists():
        console.print(f"[red]Error:[/] No agent.yaml found in {agent_dir}")
        raise SystemExit(1)

    manifest = _load_yaml(manifest_path)

    # Header
    console.print()
    console.print(f"[bold]{manifest.get('name', 'unknown')}[/] v{manifest.get('version', '?')}")
    console.print(f"  {manifest.get('description', '')}")
    console.print(f"  Domain: {manifest.get('domain', 'unspecified')} | "
                  f"Language: {manifest.get('runtime', {}).get('language', '?')} | "
                  f"AES: {manifest.get('aes', '?')}")
    console.print()

    # Skills table
    skills = manifest.get("skills", [])
    if skills:
        table = Table(title="Skills", show_header=True, header_style="bold")
        table.add_column("ID", style="cyan")
        table.add_column("Manifest")
        table.add_column("Runbook")
        table.add_column("Status")

        for skill in skills:
            manifest_exists = (agent_dir / skill.get("manifest", "")).exists() if skill.get("manifest") else False
            runbook_exists = (agent_dir / skill.get("runbook", "")).exists() if skill.get("runbook") else False
            status = "[green]OK[/]" if manifest_exists and runbook_exists else "[red]MISSING[/]"
            table.add_row(
                skill.get("id", "?"),
                skill.get("manifest", "-"),
                skill.get("runbook", "-"),
                status,
            )
        console.print(table)
        console.print()

    # Registries
    registries = manifest.get("registries", [])
    if registries:
        table = Table(title="Registries", show_header=True, header_style="bold")
        table.add_column("ID", style="cyan")
        table.add_column("Path")
        table.add_column("Description")
        table.add_column("Entries")

        for reg in registries:
            reg_path = agent_dir / reg["path"]
            entry_count = "?"
            if reg_path.exists():
                reg_data = _load_yaml(reg_path)
                categories = reg_data.get("categories", {})
                count = sum(
                    len(v) if isinstance(v, dict) else 0
                    for v in categories.values()
                )
                entry_count = str(count)

            table.add_row(
                reg.get("id", "?"),
                reg["path"],
                reg.get("description", "-"),
                entry_count,
            )
        console.print(table)
        console.print()

    # Workflows
    workflows = manifest.get("workflows", [])
    if workflows:
        for wf_ref in workflows:
            wf_path = agent_dir / wf_ref["path"]
            if wf_path.exists():
                wf_data = _load_yaml(wf_path)
                n_states = len(wf_data.get("states", {}))
                n_transitions = len(wf_data.get("transitions", []))
                console.print(f"[bold]Workflow:[/] {wf_ref['id']} ({n_states} states, {n_transitions} transitions)")
                console.print(_render_workflow_diagram(wf_data))
                console.print()

    # Commands
    commands = manifest.get("commands", [])
    if commands:
        table = Table(title="Commands", show_header=True, header_style="bold")
        table.add_column("Trigger", style="cyan")
        table.add_column("Description")
        for cmd in commands:
            table.add_row(
                cmd.get("trigger", f"/{cmd.get('id', '?')}"),
                cmd.get("description", "-"),
            )
        console.print(table)
        console.print()

    # Summary
    console.print("[bold]Summary[/]")
    console.print(f"  Skills:     {len(skills)}")
    console.print(f"  Registries: {len(registries)}")
    console.print(f"  Workflows:  {len(workflows)}")
    console.print(f"  Commands:   {len(commands)}")

    # Resources
    resources = manifest.get("resources", {})
    if resources:
        console.print(f"  CPU limit:  {resources.get('max_cpu_percent', '-')}%")
        console.print(f"  Mem limit:  {resources.get('max_memory_percent', '-')}%")
    console.print()


# ---------------------------------------------------------------------------
# Remote registry inspection
# ---------------------------------------------------------------------------

def _render_registry_metadata(name: str, pkg: dict, selected_version: str) -> None:
    """Render registry-level metadata for a package."""
    console.print()
    console.print(f"[bold]{name}[/] v{selected_version}  [dim](registry)[/]")
    console.print(f"  {pkg.get('description', '')}")
    console.print(f"  Type: {pkg.get('type', 'skill')} | "
                  f"Visibility: {pkg.get('visibility', 'public')}")

    tags = pkg.get("tags", [])
    if tags:
        console.print(f"  Tags: {', '.join(tags)}")
    console.print()

    # Versions table
    versions_dict = pkg.get("versions", {})
    if versions_dict:
        table = Table(title="Versions", show_header=True, header_style="bold")
        table.add_column("Version", style="cyan")
        table.add_column("Published")
        table.add_column("SHA256", style="dim")

        sorted_versions = sorted(
            versions_dict.items(),
            key=lambda kv: _parse_version(kv[0]),
            reverse=True,
        )

        for ver, info in sorted_versions:
            marker = " [bold green](latest)[/]" if ver == pkg.get("latest") else ""
            published = info.get("published_at", "?")
            if isinstance(published, str) and "T" in published:
                published = published.split("T")[0]
            sha_short = info.get("sha256", "?")[:12] + "..."
            table.add_row(f"{ver}{marker}", published, sha_short)

        console.print(table)
        console.print()


def _inspect_remote_skill(extract_dir: Path) -> None:
    """Render skill manifest details from an extracted package."""
    manifests = list(extract_dir.rglob("*.skill.yaml"))
    if not manifests:
        manifests = list(extract_dir.rglob("skill.yaml"))
    if not manifests:
        console.print("[dim]No skill manifest found in package.[/]")
        return

    manifest = _load_yaml(manifests[0])

    console.print("[bold]Skill Details[/]")
    console.print(f"  ID:          {manifest.get('id', '?')}")
    console.print(f"  Name:        {manifest.get('name', '?')}")
    console.print(f"  Version:     {manifest.get('version', '?')}")
    console.print(f"  Description: {manifest.get('description', '')}")
    console.print()

    # Inputs
    inputs = manifest.get("inputs", {})
    required = inputs.get("required", [])
    optional = inputs.get("optional", [])
    env_inputs = inputs.get("environment", [])

    if required or optional:
        table = Table(title="Inputs", show_header=True, header_style="bold")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Required")
        table.add_column("Description")

        for inp in required:
            table.add_row(
                inp.get("name", "?"),
                inp.get("type", "?"),
                "[green]Yes[/]",
                inp.get("description", ""),
            )
        for inp in optional:
            table.add_row(
                inp.get("name", "?"),
                inp.get("type", "?"),
                "No",
                inp.get("description", ""),
            )
        console.print(table)
        console.print()

    if env_inputs:
        console.print(f"  Environment: {', '.join(env_inputs)}")
        console.print()

    # Outputs
    outputs = manifest.get("outputs", [])
    if outputs:
        table = Table(title="Outputs", show_header=True, header_style="bold")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Description")

        for out in outputs:
            table.add_row(
                out.get("name", "?"),
                out.get("type", "?"),
                out.get("description", ""),
            )
        console.print(table)
        console.print()

    # Dependencies
    depends_on = manifest.get("depends_on", [])
    blocks = manifest.get("blocks", [])
    if depends_on or blocks:
        console.print("[bold]Dependencies[/]")
        if depends_on:
            console.print(f"  Depends on: {', '.join(str(d) for d in depends_on)}")
        if blocks:
            console.print(f"  Blocks:     {', '.join(str(b) for b in blocks)}")
        console.print()

    # Triggers
    triggers = manifest.get("triggers", [])
    if triggers:
        console.print("[bold]Triggers[/]")
        for t in triggers:
            label = t.get("command", t.get("cron", t.get("description", "")))
            console.print(f"  [{t.get('type', '?')}] {label}")
        console.print()

    # Negative triggers
    neg_triggers = manifest.get("negative_triggers", [])
    if neg_triggers:
        console.print("[bold]Negative Triggers[/]")
        for nt in neg_triggers:
            console.print(f"  [red]- {nt}[/]")
        console.print()

    # Tags
    tags = manifest.get("tags", [])
    if tags:
        console.print(f"  Tags: {', '.join(tags)}")
        console.print()


def _inspect_remote_template(extract_dir: Path) -> None:
    """Render template details by finding .agent/ and reusing local inspect."""
    for candidate in extract_dir.rglob(AGENT_DIR):
        if candidate.is_dir() and (candidate / "agent.yaml").exists():
            project_root = candidate.parent
            _inspect_local(str(project_root))
            return

    console.print("[dim]No .agent/ directory found in template package.[/]")


def _inspect_remote(target: str) -> None:
    """Inspect a remote registry package."""
    try:
        name, version_spec = parse_registry_source(target)
    except ValueError as exc:
        console.print(f"[red]Error:[/] {exc}")
        raise SystemExit(1)

    try:
        index = fetch_index()
    except Exception as exc:
        console.print(f"[red]Error:[/] Failed to fetch registry: {exc}")
        console.print("[dim]Check your network or set AES_REGISTRY_URL.[/]")
        raise SystemExit(1)

    packages = index.get("packages", {})
    if name not in packages:
        console.print(f"[red]Error:[/] Package '{name}' not found in registry.")
        console.print("[dim]Use 'aes search' to find available packages.[/]")
        raise SystemExit(1)

    pkg = packages[name]
    pkg_type = pkg.get("type", "skill")
    versions_dict = pkg.get("versions", {})

    available = list(versions_dict.keys())
    version = resolve_version(version_spec, available)
    if version is None:
        console.print(
            f"[red]Error:[/] No version of '{name}' matches '{version_spec}'. "
            f"Available: {', '.join(available)}"
        )
        raise SystemExit(1)

    # Registry metadata
    _render_registry_metadata(name, pkg, version)

    # Download and inspect package contents
    version_info = versions_dict[version]
    sha256_expected = version_info.get("sha256", "")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        try:
            tarball = download_package(name, version, sha256_expected, tmp_dir)
        except Exception as exc:
            console.print(f"[yellow]Warning:[/] Could not download package: {exc}")
            console.print("[dim]Showing registry metadata only.[/]")
            return

        with tarfile.open(tarball, "r:gz") as tar:
            _safe_extract(tar, tmp_dir)

        if pkg_type == "template":
            _inspect_remote_template(tmp_dir)
        else:
            _inspect_remote_skill(tmp_dir)


@click.command("inspect")
@click.argument("target", default=".")
def inspect_cmd(target: str) -> None:
    """Show AES project structure, or inspect a remote registry package.

    \b
    Local:   aes inspect ./my-project
    Remote:  aes inspect deploy
             aes inspect deploy@1.0.0
             aes inspect aes-hub/deploy
    """
    if _is_local_path(target):
        _inspect_local(target)
    else:
        _inspect_remote(target)
