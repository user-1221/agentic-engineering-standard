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

mcp = FastMCP("aes-registry")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def aes_search(
    query: str = "",
    tag: str = "",
    domain: str = "",
    pkg_type: str = "",
    sort_by: str = "name",
    limit: int = 0,
) -> str:
    """Search the AES package registry for skills and templates.

    Args:
        query: Keyword to search package names and descriptions.
        tag: Filter by tag (e.g. "ml", "devops").
        domain: Filter by domain (convention: domain as tag).
        pkg_type: Filter by type: "skill" or "template".
        sort_by: Sort results: "name" (alphabetical), "latest" (newest first), "version" (highest semver first).
        limit: Maximum number of results to return (0 = unlimited).

    Returns a JSON array of matching packages with version_count and latest_published_at.
    """
    try:
        results = search_packages(
            query=query or "",
            tag=tag or None,
            domain=domain or None,
            pkg_type=pkg_type or None,
        )

        # Sort
        if sort_by == "latest":
            results.sort(key=lambda p: p.get("latest_published_at", ""), reverse=True)
        elif sort_by == "version":
            from aes.registry import _parse_version
            def _ver_key(p: dict) -> tuple:
                try:
                    return _parse_version(p.get("latest", "0.0.0"))
                except ValueError:
                    return (0, 0, 0)
            results.sort(key=_ver_key, reverse=True)
        else:
            results.sort(key=lambda p: p["name"])

        # Limit
        if limit > 0:
            results = results[:limit]

        return json.dumps(results, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"Registry search failed: {exc}"})


@mcp.tool()
def aes_inspect(name: str, version: str = "") -> str:
    """Show full details about a package in the AES registry.

    Downloads the package tarball and extracts manifest details including
    inputs, outputs, dependencies, and triggers. Falls back to index
    metadata only if download fails.

    Args:
        name: Package name (e.g. "deploy") or with version (e.g. "deploy@1.0.0").
        version: Optional version constraint (e.g. "1.0.0", "^1.0"). Overrides @ syntax.
    """
    import tarfile
    import tempfile

    import yaml

    from aes.registry import (
        download_package,
        parse_registry_source,
        resolve_version,
    )
    from aes.commands.install import _safe_extract

    # Parse name and version
    try:
        parsed_name, parsed_spec = parse_registry_source(name)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    version_spec = version or parsed_spec

    try:
        index = fetch_index()
    except Exception as exc:
        return json.dumps({"error": f"Failed to fetch registry index: {exc}"})

    packages = index.get("packages", {})
    if parsed_name not in packages:
        return json.dumps({"error": f"Package '{parsed_name}' not found in registry."})

    pkg = packages[parsed_name]
    versions_dict = pkg.get("versions", {})
    available = list(versions_dict.keys())

    resolved = resolve_version(version_spec, available)
    if resolved is None:
        return json.dumps({
            "error": f"No version of '{parsed_name}' matches '{version_spec}'.",
            "available": available,
        })

    result: dict = {
        "name": parsed_name,
        "type": pkg.get("type", "skill"),
        "visibility": pkg.get("visibility", "public"),
        "description": pkg.get("description", ""),
        "tags": pkg.get("tags", []),
        "latest": pkg.get("latest", ""),
        "inspected_version": resolved,
        "versions": pkg.get("versions", {}),
    }

    # Download and extract manifest details
    version_info = versions_dict[resolved]
    sha256_expected = version_info.get("sha256", "")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            with contextlib.redirect_stdout(sys.stderr):
                tarball = download_package(parsed_name, resolved, sha256_expected, tmp_dir)

            with tarfile.open(tarball, "r:gz") as tar:
                _safe_extract(tar, tmp_dir)

            # Find skill manifest
            manifests = list(tmp_dir.rglob("*.skill.yaml"))
            if not manifests:
                manifests = list(tmp_dir.rglob("skill.yaml"))

            if manifests:
                with open(manifests[0]) as f:
                    manifest_data = yaml.safe_load(f)
                if isinstance(manifest_data, dict):
                    result["manifest"] = {
                        "id": manifest_data.get("id"),
                        "name": manifest_data.get("name"),
                        "version": manifest_data.get("version"),
                        "description": manifest_data.get("description"),
                        "inputs": manifest_data.get("inputs"),
                        "outputs": manifest_data.get("outputs"),
                        "depends_on": manifest_data.get("depends_on"),
                        "blocks": manifest_data.get("blocks"),
                        "triggers": manifest_data.get("triggers"),
                        "negative_triggers": manifest_data.get("negative_triggers"),
                        "tags": manifest_data.get("tags"),
                    }
            else:
                # Check for template (agent.yaml inside .agent/)
                agent_yamls = list(tmp_dir.rglob("agent.yaml"))
                if agent_yamls:
                    with open(agent_yamls[0]) as f:
                        agent_data = yaml.safe_load(f)
                    if isinstance(agent_data, dict):
                        result["manifest"] = {
                            "name": agent_data.get("name"),
                            "version": agent_data.get("version"),
                            "description": agent_data.get("description"),
                            "domain": agent_data.get("domain"),
                            "skills": agent_data.get("skills"),
                            "workflows": agent_data.get("workflows"),
                            "commands": agent_data.get("commands"),
                        }
    except Exception:
        result["manifest_note"] = "Could not download package; showing registry metadata only."

    return json.dumps(result, indent=2)


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
