"""aes install — Install skills from tarballs, local paths, registry, or agent.yaml deps."""

from __future__ import annotations

import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import click
import yaml
from rich.console import Console

from aes.config import AGENT_DIR, MANIFEST_FILE, SKILLS_DIR, VENDOR_DIR
from aes.i18n import t
from aes.registry import (
    download_package,
    fetch_index,
    parse_registry_source,
    resolve_version,
)

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_skill_files(directory: Path) -> Tuple[str, str, Optional[str]]:
    """Find skill manifest and runbook in a directory.

    Returns (skill_id, manifest_filename, runbook_filename_or_None).

    Handles two naming conventions:
      - Named: ``deploy.skill.yaml`` + ``deploy.md``
      - Generic: ``skill.yaml`` + ``runbook.md``
    """
    # Look for *.skill.yaml first (named convention), then skill.yaml (generic)
    named = [p for p in directory.iterdir() if p.name.endswith(".skill.yaml") and p.name != "skill.yaml"]
    generic = directory / "skill.yaml"

    if named:
        manifest_path = named[0]
    elif generic.exists():
        manifest_path = generic
    else:
        raise click.ClickException(
            f"No skill manifest (*.skill.yaml) found in {directory}"
        )

    with open(manifest_path) as f:
        manifest_data = yaml.safe_load(f) or {}

    skill_id = manifest_data.get("id")
    if not skill_id:
        raise click.ClickException(
            f"Skill manifest {manifest_path.name} is missing 'id' field"
        )

    # Determine runbook filename
    runbook_name: Optional[str] = None
    # Named convention: {id}.md
    named_runbook = directory / f"{skill_id}.md"
    generic_runbook = directory / "runbook.md"
    if named_runbook.exists():
        runbook_name = named_runbook.name
    elif generic_runbook.exists():
        runbook_name = generic_runbook.name

    return skill_id, manifest_path.name, runbook_name


def _place_in_vendor(
    src_dir: Path,
    skill_id: str,
    project_root: Path,
    force: bool,
) -> Path:
    """Copy a skill directory into ``.agent/skills/vendor/{id}/``.

    Returns the destination path.  Raises if it already exists and *force*
    is ``False``.
    """
    vendor_dir = project_root / AGENT_DIR / SKILLS_DIR / VENDOR_DIR / skill_id
    if vendor_dir.exists():
        if not force:
            raise click.ClickException(
                f"Skill '{skill_id}' already installed at {vendor_dir}. "
                "Use --force to overwrite."
            )
        shutil.rmtree(vendor_dir)

    shutil.copytree(src_dir, vendor_dir, symlinks=False)
    return vendor_dir


def _register_skill(
    project_root: Path,
    skill_id: str,
    manifest_name: str,
    runbook_name: Optional[str],
) -> None:
    """Ensure ``agent.yaml`` has an entry in ``skills:`` for *skill_id*.

    Paths are relative to ``.agent/``, e.g.
    ``skills/vendor/deploy/deploy.skill.yaml``.
    """
    manifest_path = project_root / AGENT_DIR / MANIFEST_FILE
    with open(manifest_path) as f:
        data = yaml.safe_load(f) or {}

    skills = data.setdefault("skills", [])

    # Build relative paths (relative to .agent/)
    rel_manifest = f"{SKILLS_DIR}/{VENDOR_DIR}/{skill_id}/{manifest_name}"
    rel_runbook = (
        f"{SKILLS_DIR}/{VENDOR_DIR}/{skill_id}/{runbook_name}"
        if runbook_name
        else None
    )

    entry = {"id": skill_id, "manifest": rel_manifest}
    if rel_runbook:
        entry["runbook"] = rel_runbook

    # Replace existing entry for this id, or append
    replaced = False
    for i, existing in enumerate(skills):
        if existing.get("id") == skill_id:
            skills[i] = entry
            replaced = True
            break
    if not replaced:
        skills.append(entry)

    with open(manifest_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract tarball members, rejecting path-traversal attacks.

    Safe for Python 3.9 (no ``data_filter`` yet).
    """
    for member in tar.getmembers():
        # Reject symlinks and hardlinks — they can point outside dest
        if member.issym() or member.islnk():
            raise click.ClickException(
                f"Refusing to extract symlink/hardlink: {member.name}"
            )
        member_path = os.path.normpath(member.name)
        if member_path.startswith("..") or os.path.isabs(member_path):
            raise click.ClickException(
                f"Refusing to extract path-traversal entry: {member.name}"
            )
        # Extra safety: resolve and verify it stays under dest
        target = (dest / member_path).resolve()
        if not str(target).startswith(str(dest.resolve())):
            raise click.ClickException(
                f"Refusing to extract outside target: {member.name}"
            )
    tar.extractall(dest)


# ---------------------------------------------------------------------------
# Source detection
# ---------------------------------------------------------------------------

def _detect_source_type(source: str) -> str:
    """Return one of: 'tarball', 'local', 'registry', 'git'."""
    if source.startswith("local:"):
        return "local"
    if source.startswith("github:"):
        return "git"
    if source.startswith("aes-hub/"):
        return "registry"
    # Heuristic: file extension
    if source.endswith(".tar.gz") or source.endswith(".tgz"):
        return "tarball"
    if Path(source).is_file() and tarfile.is_tarfile(source):
        return "tarball"
    if Path(source).is_dir():
        return "local"
    # If it looks like a path that doesn't exist, give a helpful error
    return "unknown"


# ---------------------------------------------------------------------------
# Install modes
# ---------------------------------------------------------------------------

def _install_tarball(tarball_path: Path, project_root: Path, force: bool) -> str:
    """Install a skill from a ``.tar.gz`` tarball.  Returns the skill id."""
    if not tarball_path.exists():
        raise click.ClickException(f"File not found: {tarball_path}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        with tarfile.open(tarball_path, "r:gz") as tar:
            _safe_extract(tar, tmp_dir)

        # The tarball should contain a single top-level directory
        children = [p for p in tmp_dir.iterdir() if p.is_dir()]
        if len(children) == 1:
            skill_dir = children[0]
        else:
            skill_dir = tmp_dir

        skill_id, manifest_name, runbook_name = _find_skill_files(skill_dir)
        _place_in_vendor(skill_dir, skill_id, project_root, force)
        _register_skill(project_root, skill_id, manifest_name, runbook_name)

    return skill_id


def _install_local(source: str, project_root: Path, force: bool) -> str:
    """Install a skill from a local directory.  Returns the skill id."""
    # Strip ``local:`` prefix if present
    dir_path = Path(source.removeprefix("local:")).resolve()
    if not dir_path.is_dir():
        raise click.ClickException(f"Directory not found: {dir_path}")

    skill_id, manifest_name, runbook_name = _find_skill_files(dir_path)
    _place_in_vendor(dir_path, skill_id, project_root, force)
    _register_skill(project_root, skill_id, manifest_name, runbook_name)
    return skill_id


def _install_registry(source: str, project_root: Path, force: bool) -> str:
    """Install a skill from the AES registry.  Returns the skill id."""
    name, version_spec = parse_registry_source(source)

    try:
        index = fetch_index()
    except Exception as exc:
        raise click.ClickException(f"Failed to fetch registry index: {exc}")

    packages = index.get("packages", {})
    if name not in packages:
        raise click.ClickException(
            f"Package '{name}' not found in registry. "
            "Use 'aes search' to find available packages."
        )

    pkg = packages[name]
    available = list(pkg.get("versions", {}).keys())
    version = resolve_version(version_spec, available)
    if version is None:
        raise click.ClickException(
            f"No version of '{name}' matches '{version_spec}'. "
            f"Available: {', '.join(available)}"
        )

    version_info = pkg["versions"][version]
    sha256_expected = version_info["sha256"]

    console.print(f"[dim]{t('install.downloading', name=name, version=version)}[/]")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        try:
            tarball = download_package(name, version, sha256_expected, tmp_dir)
        except Exception as exc:
            raise click.ClickException(f"Failed to download {name}@{version}: {exc}")

        return _install_tarball(tarball, project_root, force)


def _install_from_deps(project_root: Path, force: bool) -> None:
    """Install all dependencies declared in ``agent.yaml``."""
    manifest_path = project_root / AGENT_DIR / MANIFEST_FILE
    if not manifest_path.exists():
        raise click.ClickException("No agent.yaml found")

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f) or {}

    deps = manifest.get("dependencies", {}).get("skills", {})
    if not deps:
        console.print(f"[dim]{t('install.no_deps')}[/]")
        return

    installed = 0
    skipped = 0
    errored = 0

    for name, source in deps.items():
        source_type = _detect_source_type(source)
        try:
            if source_type == "local":
                _install_local(source, project_root, force)
                console.print(f"  [green]{t('install.installed')}[/] {name} ← {source}")
                installed += 1
            elif source_type == "tarball":
                _install_tarball(Path(source), project_root, force)
                console.print(f"  [green]{t('install.installed')}[/] {name} ← {source}")
                installed += 1
            elif source_type == "registry":
                _install_registry(source, project_root, force)
                console.print(f"  [green]{t('install.installed')}[/] {name} ← {source}")
                installed += 1
            elif source_type == "git":
                console.print(
                    f"  [yellow]{t('install.skipped_git', name=name)}[/]"
                )
                skipped += 1
            else:
                console.print(f"  [red]{t('install.error_unknown_source', name=name, source=source)}[/]")
                errored += 1
        except click.ClickException as exc:
            console.print(f"  [red]{t('install.error_dep', name=name, exc=exc.format_message())}[/]")
            errored += 1

    console.print()
    console.print(
        f"[bold]{t('common.summary')}:[/] {t('install.dep_summary', installed=installed, skipped=skipped, errored=errored)}"
    )


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------

@click.command("install")
@click.argument("source", required=False)
@click.option(
    "--path",
    default=".",
    type=click.Path(exists=True),
    help="Project root directory",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing vendor skills",
)
def install_cmd(source: Optional[str], path: str, force: bool) -> None:
    """Install skill dependencies.

    If SOURCE is provided, install a specific skill from a tarball or local
    directory.  Without SOURCE, install all dependencies from agent.yaml.

    \b
    Examples:
      aes install ./deploy-1.0.0.tar.gz          # from tarball
      aes install ../shared-skills/monitoring     # from local dir
      aes install local:../shared-skills/deploy   # explicit local prefix
      aes install                                 # all deps from agent.yaml
    """
    project_root = Path(path).resolve()
    agent_dir = project_root / AGENT_DIR

    if not agent_dir.exists():
        console.print(f"[red]{t('common.error')}:[/] {t('common.no_agent_dir', agent_dir=AGENT_DIR, path=project_root)}")
        raise SystemExit(1)

    if source is None:
        _install_from_deps(project_root, force)
        return

    source_type = _detect_source_type(source)

    if source_type == "tarball":
        skill_id = _install_tarball(Path(source).resolve(), project_root, force)
        console.print(f"[green]{t('install.installed_skill')}[/] {skill_id}")
    elif source_type == "local":
        skill_id = _install_local(source, project_root, force)
        console.print(f"[green]{t('install.installed_skill')}[/] {skill_id}")
    elif source_type == "registry":
        skill_id = _install_registry(source, project_root, force)
        console.print(f"[green]{t('install.installed_skill')}[/] {skill_id}")
    elif source_type == "git":
        console.print(
            f"[yellow]{t('install.git_not_supported', source=source)}[/]"
        )
        console.print(f"[dim]{t('install.tarball_local_only')}[/]")
    else:
        raise click.ClickException(
            f"Cannot determine source type for '{source}'. "
            "Provide a .tar.gz file, a directory path, or use the local: prefix."
        )
