"""AES CLI entry point."""

from __future__ import annotations

import os
import sys
from typing import Optional

import click

from aes.commands.init import init_cmd
from aes.commands.validate import validate_cmd
from aes.commands.inspect import inspect_cmd
from aes.commands.publish import publish_cmd
from aes.commands.install import install_cmd
from aes.commands.search import search_cmd
from aes.commands.status import status_cmd
from aes.commands.sync import sync_cmd
from aes.commands.upgrade import upgrade_cmd
from aes.commands.bom import bom_cmd


def _prompt_language() -> None:
    """One-time language selection prompt (bilingual)."""
    from rich.console import Console
    from aes.global_config import set_locale
    from aes.i18n._messages import MESSAGES

    console = Console()
    console.print()
    console.print(f"[bold]{MESSAGES['lang.title']}[/]")
    console.print()
    console.print(f"  [bold cyan][1][/] {MESSAGES['lang.english']}")
    console.print(f"  [bold cyan][2][/] {MESSAGES['lang.japanese']}")
    console.print()

    choice = click.prompt(
        MESSAGES["lang.prompt"],
        type=click.IntRange(1, 2),
        default=1,
    )
    locale = "en" if choice == 1 else "ja"
    set_locale(locale)


@click.group()
@click.version_option(package_name="aes-cli")
@click.option("--lang", default=None, hidden=True, help="Override language (en/ja)")
def cli(lang: Optional[str] = None) -> None:
    """AES — Agentic Engineering Standard CLI.

    Scaffold, validate, inspect, and share agentic engineering projects.
    """
    from aes.i18n import init_locale

    # Priority: --lang flag > AES_LANG env > ~/.aes/config.yaml > first-run prompt
    if lang:
        init_locale(lang)
        return

    env_lang = os.environ.get("AES_LANG")
    if env_lang:
        init_locale(env_lang)
        return

    from aes.global_config import get_locale
    saved = get_locale()
    if saved is None and sys.stdin.isatty():
        _prompt_language()

    init_locale()


cli.add_command(init_cmd, "init")
cli.add_command(validate_cmd, "validate")
cli.add_command(inspect_cmd, "inspect")
cli.add_command(publish_cmd, "publish")
cli.add_command(install_cmd, "install")
cli.add_command(sync_cmd, "sync")
cli.add_command(status_cmd, "status")
cli.add_command(search_cmd, "search")
cli.add_command(upgrade_cmd, "upgrade")
cli.add_command(bom_cmd, "bom")


if __name__ == "__main__":
    cli()
