"""aes validate — Validate .agent/ files against schemas."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from aes.config import AGENT_DIR
from aes.validator import validate_agent_dir

console = Console()


@click.command("validate")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--strict", is_flag=True, help="Promote quality warnings to errors.")
def validate_cmd(path: str, strict: bool) -> None:
    """Validate all .agent/ files against AES schemas.

    PATH is the project root directory (default: current directory).
    """
    project_root = Path(path).resolve()
    agent_dir = project_root / AGENT_DIR

    if not agent_dir.exists():
        console.print(f"[red]Error:[/] No {AGENT_DIR}/ directory found at {project_root}")
        console.print("[dim]Run 'aes init' to create one.[/]")
        raise SystemExit(1)

    console.print(f"[bold]Validating[/] {agent_dir}")
    console.print()

    results = validate_agent_dir(agent_dir)

    passed = 0
    failed = 0
    warnings = 0

    for result in results:
        rel_path = result.file_path.relative_to(project_root)
        is_warning = result.valid and result.errors
        if is_warning and strict:
            # Promote warnings to errors in strict mode
            console.print(f"  [red]FAIL[/] {rel_path}")
            for error in result.errors:
                console.print(f"       {error}")
            failed += 1
        elif is_warning:
            console.print(f"  [yellow]WARN[/] {rel_path}")
            for error in result.errors:
                console.print(f"       {error}")
            warnings += 1
        elif result.valid:
            console.print(f"  [green]PASS[/] {rel_path}")
            passed += 1
        else:
            console.print(f"  [red]FAIL[/] {rel_path}")
            for error in result.errors:
                console.print(f"       {error}")
            failed += 1

    console.print()
    summary_parts = []
    if passed:
        summary_parts.append(f"{passed} passed")
    if warnings:
        summary_parts.append(f"{warnings} warning(s)")
    if failed:
        summary_parts.append(f"{failed} failed")

    if failed == 0:
        console.print(f"[green]All valid.[/] {', '.join(summary_parts)}.")
    else:
        console.print(f"[red]{', '.join(summary_parts)}.[/]")
        raise SystemExit(1)
