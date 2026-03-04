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
def validate_cmd(path: str) -> None:
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

    for result in results:
        rel_path = result.file_path.relative_to(project_root)
        if result.valid:
            console.print(f"  [green]PASS[/] {rel_path}")
            passed += 1
        else:
            console.print(f"  [red]FAIL[/] {rel_path}")
            for error in result.errors:
                console.print(f"       {error}")
            failed += 1

    console.print()
    if failed == 0:
        console.print(f"[green]All {passed} files valid.[/]")
    else:
        console.print(f"[red]{failed} file(s) failed[/], {passed} passed.")
        raise SystemExit(1)
