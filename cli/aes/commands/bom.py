"""aes bom — Display the Agent Bill of Materials."""

from __future__ import annotations

from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from aes.config import AGENT_DIR, BOM_FILE
from aes.i18n import t

console = Console()


def _load_bom(agent_dir: Path) -> dict:
    """Load and return bom.yaml, or empty dict."""
    bom_path = agent_dir / BOM_FILE
    if not bom_path.exists():
        return {}
    with open(bom_path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


@click.command("bom")
@click.argument("path", default=".", type=click.Path(exists=True))
def bom_cmd(path: str) -> None:
    """Display the Agent Bill of Materials (AI-BOM).

    Shows all models, frameworks, tools, and data sources
    declared in .agent/bom.yaml.

    \b
    Examples:
      aes bom                    # current project
      aes bom ./my-project       # specific project
    """
    project_root = Path(path).resolve()
    agent_dir = project_root / AGENT_DIR

    if not agent_dir.exists():
        console.print(f"[red]{t('common.error')}:[/] {t('common.no_agent_dir', agent_dir=AGENT_DIR, path=project_root)}")
        raise SystemExit(1)

    bom = _load_bom(agent_dir)
    if not bom:
        console.print(f"\n  [dim]{t('bom.not_found')}[/]\n")
        return

    console.print(f"\n[bold]{t('bom.title')}[/]  [dim](AES {bom.get('aes_bom', '?')})[/]\n")

    # Models
    models = bom.get("models", [])
    if models:
        table = Table(title=t("bom.models_table"), show_header=True, header_style="bold")
        table.add_column(t("bom.col_name"), style="cyan")
        table.add_column(t("bom.col_provider"))
        table.add_column(t("bom.col_purpose"))
        table.add_column(t("bom.col_license"))
        for m in models:
            table.add_row(
                m.get("name", "?"),
                m.get("provider", "?"),
                m.get("purpose", "-"),
                m.get("license", "-"),
            )
        console.print(table)
        console.print()

    # Frameworks
    frameworks = bom.get("frameworks", [])
    if frameworks:
        table = Table(title=t("bom.frameworks_table"), show_header=True, header_style="bold")
        table.add_column(t("bom.col_name"), style="cyan")
        table.add_column(t("bom.col_version"))
        table.add_column(t("bom.col_license"))
        for fw in frameworks:
            table.add_row(
                fw.get("name", "?"),
                fw.get("version", "-"),
                fw.get("license", "-"),
            )
        console.print(table)
        console.print()

    # Tools
    tools = bom.get("tools", [])
    if tools:
        table = Table(title=t("bom.tools_table"), show_header=True, header_style="bold")
        table.add_column(t("bom.col_name"), style="cyan")
        table.add_column(t("bom.col_type"))
        table.add_column(t("bom.col_version"))
        table.add_column(t("bom.col_source"))
        for tool in tools:
            table.add_row(
                tool.get("name", "?"),
                tool.get("type", "?"),
                tool.get("version", "-"),
                tool.get("source", "-"),
            )
        console.print(table)
        console.print()

    # Data Sources
    data_sources = bom.get("data_sources", [])
    if data_sources:
        table = Table(title=t("bom.data_sources_table"), show_header=True, header_style="bold")
        table.add_column(t("bom.col_name"), style="cyan")
        table.add_column(t("bom.col_type"))
        table.add_column(t("bom.col_uri"))
        table.add_column(t("bom.col_license"))
        for ds in data_sources:
            table.add_row(
                ds.get("name", "?"),
                ds.get("type", "?"),
                ds.get("uri", "-"),
                ds.get("license", "-"),
            )
        console.print(table)
        console.print()

    # Summary
    console.print(f"[bold]{t('bom.summary')}[/]")
    console.print(f"  {t('bom.models_count', count=len(models))}")
    console.print(f"  {t('bom.frameworks_count', count=len(frameworks))}")
    console.print(f"  {t('bom.tools_count', count=len(tools))}")
    console.print(f"  {t('bom.data_sources_count', count=len(data_sources))}")
    console.print()
