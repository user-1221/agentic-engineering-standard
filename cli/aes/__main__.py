"""AES CLI entry point."""

from __future__ import annotations

import click

from aes.commands.init import init_cmd
from aes.commands.validate import validate_cmd
from aes.commands.inspect import inspect_cmd
from aes.commands.publish import publish_cmd
from aes.commands.install import install_cmd
from aes.commands.search import search_cmd
from aes.commands.status import status_cmd
from aes.commands.sync import sync_cmd


@click.group()
@click.version_option(package_name="aes-cli")
def cli() -> None:
    """AES — Agentic Engineering Standard CLI.

    Scaffold, validate, inspect, and share agentic engineering projects.
    """


cli.add_command(init_cmd, "init")
cli.add_command(validate_cmd, "validate")
cli.add_command(inspect_cmd, "inspect")
cli.add_command(publish_cmd, "publish")
cli.add_command(install_cmd, "install")
cli.add_command(sync_cmd, "sync")
cli.add_command(status_cmd, "status")
cli.add_command(search_cmd, "search")


if __name__ == "__main__":
    cli()
