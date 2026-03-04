"""aes inspect — Show project structure and stats."""

from __future__ import annotations

from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from aes.config import AGENT_DIR

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


@click.command("inspect")
@click.argument("path", default=".", type=click.Path(exists=True))
def inspect_cmd(path: str) -> None:
    """Show AES project structure and statistics.

    PATH is the project root directory (default: current directory).
    """
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
