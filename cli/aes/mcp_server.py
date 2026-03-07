"""AES MCP Server — Model Context Protocol server for the AES registry."""

from __future__ import annotations

import contextlib
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from aes.config import AGENT_DIR
from aes.registry import fetch_index, search_packages
from aes.validator import validate_agent_dir

# Logging must go to stderr — stdout is the JSON-RPC channel
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("aes-mcp")

mcp = FastMCP("aes-registry", version="0.1.0")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def aes_search(
    query: str = "",
    tag: str = "",
    domain: str = "",
    pkg_type: str = "",
) -> str:
    """Search the AES package registry for skills and templates.

    Args:
        query: Keyword to search package names and descriptions.
        tag: Filter by tag (e.g. "ml", "devops").
        domain: Filter by domain (convention: domain as tag).
        pkg_type: Filter by type: "skill" or "template".

    Returns a JSON array of matching packages.
    """
    try:
        results = search_packages(
            query=query or "",
            tag=tag or None,
            domain=domain or None,
            pkg_type=pkg_type or None,
        )
        return json.dumps(results, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"Registry search failed: {exc}"})


@mcp.tool()
def aes_inspect(name: str) -> str:
    """Show details about a specific package in the AES registry.

    Returns all versions, description, tags, and metadata for the package.

    Args:
        name: Package name to inspect.
    """
    try:
        index = fetch_index()
    except Exception as exc:
        return json.dumps({"error": f"Failed to fetch registry index: {exc}"})

    packages = index.get("packages", {})
    if name not in packages:
        return json.dumps({"error": f"Package '{name}' not found in registry."})

    pkg = packages[name]
    return json.dumps(
        {
            "name": name,
            "type": pkg.get("type", "skill"),
            "description": pkg.get("description", ""),
            "tags": pkg.get("tags", []),
            "latest": pkg.get("latest", ""),
            "versions": pkg.get("versions", {}),
        },
        indent=2,
    )


@mcp.tool()
def aes_install(
    source: str,
    project_path: str = ".",
    force: bool = False,
) -> str:
    """Install a skill or template from the AES registry into the project.

    Installs into the .agent/skills/vendor/ directory and registers in agent.yaml.

    Args:
        source: Package source — registry ref (e.g. "aes-hub/deploy@^1.0"),
                local path, or tarball path.
        project_path: Project root directory (defaults to current directory).
        force: Overwrite existing vendor skills if True.
    """
    import click

    from aes.commands.install import (
        _detect_source_type,
        _install_local,
        _install_registry,
        _install_tarball,
    )

    project_root = Path(project_path).resolve()
    agent_dir = project_root / AGENT_DIR

    if not agent_dir.exists():
        return json.dumps(
            {"error": f"No {AGENT_DIR}/ directory found at {project_root}"}
        )

    source_type = _detect_source_type(source)

    if source_type == "git":
        return json.dumps({"error": "Git sources are not yet supported."})
    if source_type == "unknown":
        return json.dumps(
            {"error": f"Cannot determine source type for '{source}'."}
        )

    try:
        # Redirect stdout to stderr so rich.console.print doesn't corrupt
        # the stdio JSON-RPC channel.
        with contextlib.redirect_stdout(sys.stderr):
            if source_type == "registry":
                skill_id = _install_registry(source, project_root, force)
            elif source_type == "tarball":
                skill_id = _install_tarball(
                    Path(source).resolve(), project_root, force
                )
            elif source_type == "local":
                skill_id = _install_local(source, project_root, force)
            else:
                return json.dumps({"error": f"Unsupported source type: {source_type}"})

        return json.dumps(
            {
                "installed": skill_id,
                "vendor_path": f".agent/skills/vendor/{skill_id}",
            }
        )
    except click.ClickException as exc:
        return json.dumps({"error": exc.format_message()})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def aes_validate(project_path: str = ".") -> str:
    """Validate the .agent/ directory against AES schemas.

    Reports pass/fail for each file and any validation errors.

    Args:
        project_path: Project root directory (defaults to current directory).
    """
    project_root = Path(project_path).resolve()
    agent_dir = project_root / AGENT_DIR

    if not agent_dir.exists():
        return json.dumps(
            {"error": f"No {AGENT_DIR}/ directory found at {project_root}"}
        )

    try:
        results = validate_agent_dir(agent_dir)
    except Exception as exc:
        return json.dumps({"error": f"Validation failed: {exc}"})

    passed = sum(1 for r in results if r.valid)
    failed = sum(1 for r in results if not r.valid)

    return json.dumps(
        {
            "summary": {"passed": passed, "failed": failed, "total": len(results)},
            "results": [
                {
                    "file": str(r.file_path),
                    "schema": r.schema_type,
                    "valid": r.valid,
                    "errors": r.errors,
                }
                for r in results
            ],
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the AES MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
