"""aes search — Search the AES package registry."""

from __future__ import annotations

from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from aes.i18n import t
from aes.registry import fetch_index, search_packages, _parse_version

console = Console()


def _sort_results(results: list, sort_by: str) -> list:
    """Sort search results by the given key."""
    if sort_by == "latest":
        return sorted(
            results,
            key=lambda p: p.get("latest_published_at", ""),
            reverse=True,
        )
    elif sort_by == "version":
        def _ver_key(p: dict) -> tuple:
            try:
                return _parse_version(p.get("latest", "0.0.0"))
            except ValueError:
                return (0, 0, 0)
        return sorted(results, key=_ver_key, reverse=True)
    else:
        return sorted(results, key=lambda p: p["name"])


@click.command("search")
@click.argument("query", default="")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--domain", default=None, help="Filter by domain (convention: domain as tag)")
@click.option("--type", "pkg_type", default=None, type=click.Choice(["skill", "template"]), help="Filter by package type")
@click.option("--sort-by", "sort_by", default="name", type=click.Choice(["name", "latest", "version"]), help="Sort results")
@click.option("--limit", "limit", default=None, type=int, help="Show only first N results")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show version count and publish date")
def search_cmd(
    query: str,
    tag: Optional[str],
    domain: Optional[str],
    pkg_type: Optional[str],
    sort_by: str,
    limit: Optional[int],
    verbose: bool,
) -> None:
    """Search the AES package registry.

    \b
    Examples:
      aes search "deploy"              # keyword search
      aes search --tag ml              # filter by tag
      aes search --domain devops       # filter by domain
      aes search --type template       # filter by type
      aes search --sort-by version     # sort by semver (highest first)
      aes search --limit 5             # show top 5 results
      aes search -v                    # verbose: show version count + date
      aes search                       # list all packages
    """
    try:
        index = fetch_index()
    except Exception as exc:
        console.print(f"[red]{t('common.error')}:[/] {t('search.fetch_failed', exc=exc)}")
        console.print(f"[dim]{t('search.network_hint')}[/]")
        raise SystemExit(1)

    results = search_packages(query=query, tag=tag, domain=domain, index=index, pkg_type=pkg_type)

    if not results:
        if query:
            console.print(f"[dim]{t('search.no_match', query=query)}[/]")
        else:
            console.print(f"[dim]{t('search.no_packages')}[/]")
        return

    total = len(results)
    sorted_results = _sort_results(results, sort_by)

    if limit is not None and limit > 0:
        sorted_results = sorted_results[:limit]

    table = Table(title=t("search.table_title"))
    table.add_column(t("search.col_name"), style="bold")
    table.add_column(t("search.col_type"), style="cyan")
    table.add_column(t("search.col_latest"))
    table.add_column(t("search.col_description"))
    table.add_column(t("search.col_tags"), style="dim")
    if verbose:
        table.add_column(t("search.col_versions"), style="dim")
        table.add_column(t("search.col_published"), style="dim")

    for pkg in sorted_results:
        row = [
            str(pkg["name"]),
            str(pkg.get("type", "skill")),
            str(pkg["latest"]),
            str(pkg["description"]),
            ", ".join(str(tg) for tg in pkg.get("tags", [])),
        ]
        if verbose:
            row.append(str(pkg.get("version_count", len(pkg.get("versions", [])))))
            published = pkg.get("latest_published_at", "?")
            if isinstance(published, str) and "T" in published:
                published = published.split("T")[0]
            row.append(str(published))
        table.add_row(*row)

    console.print(table)

    shown = len(sorted_results)
    if limit is not None and shown < total:
        console.print(f"\n[dim]{t('search.shown_of_total', shown=shown, total=total, limit=limit)}[/]")
    else:
        console.print(f"\n[dim]{t('search.total_found', total=total)}[/]")
