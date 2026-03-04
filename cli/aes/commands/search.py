"""aes search — Search the AES package registry."""

from __future__ import annotations

from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from aes.registry import fetch_index, search_packages

console = Console()


@click.command("search")
@click.argument("query", default="")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--domain", default=None, help="Filter by domain (convention: domain as tag)")
@click.option("--type", "pkg_type", default=None, type=click.Choice(["skill", "template"]), help="Filter by package type")
def search_cmd(query: str, tag: Optional[str], domain: Optional[str], pkg_type: Optional[str]) -> None:
    """Search the AES package registry.

    \b
    Examples:
      aes search "deploy"              # keyword search
      aes search --tag ml              # filter by tag
      aes search --domain devops       # filter by domain
      aes search --type template       # filter by type
      aes search                       # list all packages
    """
    try:
        index = fetch_index()
    except Exception as exc:
        console.print(f"[red]Error:[/] Failed to fetch registry: {exc}")
        console.print("[dim]Check your network or set AES_REGISTRY_URL.[/]")
        raise SystemExit(1)

    results = search_packages(query=query, tag=tag, domain=domain, index=index, pkg_type=pkg_type)

    if not results:
        if query:
            console.print(f"[dim]No packages matching '{query}'.[/]")
        else:
            console.print("[dim]No packages found in registry.[/]")
        return

    table = Table(title="AES Registry")
    table.add_column("Name", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Latest")
    table.add_column("Description")
    table.add_column("Tags", style="dim")

    for pkg in sorted(results, key=lambda p: p["name"]):
        table.add_row(
            str(pkg["name"]),
            str(pkg.get("type", "skill")),
            str(pkg["latest"]),
            str(pkg["description"]),
            ", ".join(str(t) for t in pkg.get("tags", [])),
        )

    console.print(table)
    console.print(f"\n[dim]{len(results)} package(s) found.[/]")
