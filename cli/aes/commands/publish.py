"""aes publish — Package skills and templates as tarballs for sharing."""

from __future__ import annotations

import fnmatch
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional

import click
import yaml
from rich.console import Console

from aes.config import AGENT_DIR, MANIFEST_FILE
from aes.i18n import t

console = Console()

# Files/patterns excluded from template packages by default (privacy-sensitive)
_TEMPLATE_DEFAULT_EXCLUDES = [
    "memory/**", "local.yaml", "overrides/**",
    ".env", ".env.*", "*.pem", "*.key", "secrets/**",
]


def _publish_skill_dir(skill_dir: Path, output_dir: Path) -> Path:
    """Package a skill directory as ``{id}-{version}.tar.gz``.

    Returns the tarball path.
    """
    manifests = list(skill_dir.glob("*.skill.yaml")) + list(skill_dir.glob("skill.yaml"))
    if not manifests:
        raise click.ClickException(
            f"No skill manifest (*.skill.yaml) found in {skill_dir}"
        )

    manifest_path = manifests[0]
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    skill_id = manifest.get("id", "unknown")
    skill_version = manifest.get("version", "0.0.0")

    tarball_name = f"{skill_id}-{skill_version}.tar.gz"
    tarball_path = output_dir / tarball_name

    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(skill_dir, arcname=skill_id)

    return tarball_path


def _publish_from_manifest(
    project_root: Path,
    output_dir: Path,
    skill_filter: Optional[str],
) -> int:
    """Publish skills listed in ``agent.yaml``.

    Returns the number of skills published.
    """
    manifest_path = project_root / AGENT_DIR / MANIFEST_FILE
    if not manifest_path.exists():
        raise click.ClickException(
            f"No {AGENT_DIR}/{MANIFEST_FILE} found at {project_root}"
        )

    with open(manifest_path) as f:
        data = yaml.safe_load(f) or {}

    skills = data.get("skills", [])
    if not skills:
        console.print(f"[dim]{t('publish.no_skills')}[/]")
        return 0

    agent_dir = project_root / AGENT_DIR
    published = 0

    for skill_ref in skills:
        skill_id = skill_ref.get("id")
        if not skill_id:
            continue
        if skill_filter and skill_id != skill_filter:
            continue

        manifest_rel = skill_ref.get("manifest")
        if not manifest_rel:
            console.print(f"  [yellow]{t('publish.skipped_no_manifest', skill_id=skill_id)}[/]")
            continue

        manifest_file = agent_dir / manifest_rel
        if not manifest_file.exists():
            console.print(f"  [yellow]{t('publish.skipped_not_found', skill_id=skill_id, path=manifest_rel)}[/]")
            continue

        # Determine if the skill lives in its own directory or is flat
        skill_parent = manifest_file.parent
        # Check if directory is dedicated to this skill (contains only this skill's files)
        # If the manifest's parent has other skill manifests, it's a flat layout
        other_manifests = [
            p for p in skill_parent.glob("*.skill.yaml")
            if p != manifest_file
        ] + [
            p for p in skill_parent.glob("skill.yaml")
            if p != manifest_file
        ]

        if not other_manifests:
            # Dedicated directory — publish directly
            tarball = _publish_skill_dir(skill_parent, output_dir)
        else:
            # Flat layout — gather files into a temp dir
            with tempfile.TemporaryDirectory() as tmp:
                staging = Path(tmp) / skill_id
                staging.mkdir()
                # Copy manifest
                shutil.copy2(manifest_file, staging / manifest_file.name)
                # Copy runbook if declared
                runbook_rel = skill_ref.get("runbook")
                if runbook_rel:
                    runbook_file = agent_dir / runbook_rel
                    if runbook_file.exists():
                        shutil.copy2(runbook_file, staging / runbook_file.name)
                tarball = _publish_skill_dir(staging, output_dir)

        console.print(
            f"  [green]{t('publish.published_tarball', name=tarball.name, size=f'{tarball.stat().st_size / 1024:.1f}')}[/]"
        )
        published += 1

    if skill_filter and published == 0:
        raise click.ClickException(f"Skill '{skill_filter}' not found in agent.yaml")

    return published


def _is_excluded(rel_path: str, patterns: List[str]) -> bool:
    """Check if *rel_path* matches any exclusion pattern."""
    for pattern in patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Also check just the filename for non-glob patterns
        if "/" not in pattern and fnmatch.fnmatch(Path(rel_path).name, pattern):
            return True
    return False


def _validate_before_publish(project_root: Path) -> bool:
    """Validate the .agent/ directory before publishing.

    Returns True if validation passes, False otherwise.
    """
    from aes.validator import validate_agent_dir

    agent_dir = project_root / AGENT_DIR
    if not agent_dir.exists():
        console.print(f"[red]{t('common.error')}:[/] {t('common.no_agent_dir', agent_dir=AGENT_DIR, path=project_root)}")
        return False

    results = validate_agent_dir(agent_dir)
    failures = [r for r in results if not r.valid]
    if failures:
        console.print(f"[red]{t('publish.validation_failed')}[/]")
        for r in failures:
            for err in r.errors:
                console.print(f"  {r.file_path.name}: {err}")
        return False
    return True


def _publish_template_dir(
    project_root: Path,
    output_dir: Path,
    exclude_patterns: Optional[List[str]] = None,
    include_memory: bool = False,
    include_all: bool = False,
) -> Path:
    """Package a complete .agent/ directory as ``{name}-{version}.tar.gz``.

    Returns the tarball path.
    """
    agent_dir = project_root / AGENT_DIR
    manifest_path = agent_dir / MANIFEST_FILE
    if not manifest_path.exists():
        raise click.ClickException(
            f"No {AGENT_DIR}/{MANIFEST_FILE} found at {project_root}"
        )

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f) or {}

    name = manifest.get("name", "unknown")
    version = manifest.get("version", "0.0.0")

    # Build exclusion list
    if include_all:
        excludes: List[str] = []
    else:
        excludes = list(_TEMPLATE_DEFAULT_EXCLUDES)
        if include_memory:
            excludes = [p for p in excludes if not p.startswith("memory")]
    if exclude_patterns:
        excludes.extend(exclude_patterns)

    tarball_name = f"{name}-{version}.tar.gz"
    tarball_path = output_dir / tarball_name

    with tarfile.open(tarball_path, "w:gz") as tar:
        for file_path in sorted(agent_dir.rglob("*")):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(agent_dir)
            rel_str = str(rel)
            if _is_excluded(rel_str, excludes):
                continue
            arcname = f"{name}/{AGENT_DIR}/{rel_str}"
            tar.add(file_path, arcname=arcname)

    return tarball_path


def _prompt_visibility() -> str:
    """Interactively prompt the user for package visibility."""
    console.print(f"\n[bold]{t('publish.visibility_title')}[/]\n")
    choices = [
        ("public", t("publish.visibility_public")),
        ("private", t("publish.visibility_private")),
    ]
    for i, (name, desc) in enumerate(choices, 1):
        console.print(f"  [bold cyan][{i}][/] {name} — {desc}")
    console.print()
    idx = click.prompt(t("common.choice"), type=click.IntRange(1, len(choices)), default=1)
    return choices[idx - 1][0]


def _upload_to_registry(
    tarball: Path,
    skill_id: str,
    version: str,
    description: str,
    tags: Optional[list] = None,
    pkg_type: str = "skill",
    visibility: str = "public",
) -> None:
    """Upload a single tarball to the AES registry."""
    from aes.registry import upload_package

    try:
        upload_package(tarball, skill_id, version, description, tags,
                       pkg_type=pkg_type, visibility=visibility)
        console.print(f"  [green]{t('publish.uploaded', id=skill_id, version=version)}[/]")
    except RuntimeError as exc:
        console.print(f"  [red]{t('publish.upload_failed', exc=exc)}[/]")
    except Exception as exc:
        console.print(f"  [red]{t('publish.upload_error', exc=exc)}[/]")


def _upload_tarballs_from_dir(
    output_dir: Path,
    project_root: Path,
    skill_filter: Optional[str],
    visibility: str = "public",
) -> None:
    """Upload all tarballs in *output_dir* to the registry."""
    for tarball in sorted(output_dir.glob("*.tar.gz")):
        # Extract id and version from filename: {id}-{version}.tar.gz
        stem = tarball.name.removesuffix(".tar.gz")
        parts = stem.rsplit("-", 1)
        if len(parts) != 2:
            continue
        sid, sver = parts
        if skill_filter and sid != skill_filter:
            continue

        # Try to read description from the tarball manifest
        description = f"Skill: {sid}"
        tags = None
        try:
            import tarfile as _tf
            with _tf.open(tarball, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith(".skill.yaml"):
                        f = tar.extractfile(member)
                        if f:
                            mdata = yaml.safe_load(f.read())
                            description = mdata.get("description", description)
                            tags = mdata.get("tags")
                            break
        except Exception:
            pass

        _upload_to_registry(tarball, sid, sver, description, tags, visibility=visibility)


@click.command("publish")
@click.argument("skill_path", required=False, type=click.Path(exists=True))
@click.option("--output", "-o", default=".", type=click.Path(), help="Output directory for tarball(s)")
@click.option("--path", default=".", type=click.Path(exists=True), help="Project root (used when no SKILL_PATH)")
@click.option("--skill", default=None, help="Publish a single skill by id (used when no SKILL_PATH)")
@click.option("--registry", is_flag=True, default=False, help="Also upload to the AES registry")
@click.option("--template", is_flag=True, default=False, help="Publish entire .agent/ directory as a template")
@click.option("--include-memory", is_flag=True, default=False, help="Include memory/ in template (excluded by default)")
@click.option("--exclude", multiple=True, help="Additional glob patterns to exclude from template")
@click.option("--include-all", is_flag=True, default=False, help="No default exclusions for template")
@click.option("--visibility", type=click.Choice(["public", "private"]), default=None,
              help="Package visibility (public/private). Prompts if interactive, defaults to public in CI.")
def publish_cmd(
    skill_path: Optional[str],
    output: str,
    path: str,
    skill: Optional[str],
    registry: bool,
    template: bool,
    include_memory: bool,
    exclude: tuple,
    include_all: bool,
    visibility: Optional[str],
) -> None:
    """Package skill(s) or a template as tarball(s) for sharing.

    With SKILL_PATH, packages that single directory.  Without SKILL_PATH,
    reads agent.yaml and packages every listed skill (or one with --skill).

    Use --template to package the entire .agent/ directory as a template.
    Use --registry to also upload the tarball(s) to the AES registry.

    \b
    Examples:
      aes publish ./my-skill -o /tmp          # explicit directory
      aes publish -o dist/                     # all skills from agent.yaml
      aes publish --skill train -o dist/       # single skill by id
      aes publish --skill train --registry     # publish to registry
      aes publish --template -o dist/          # publish .agent/ as template
      aes publish --template --include-memory  # include memory/ in template
    """
    output_dir = Path(output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if registry and visibility is None:
        if sys.stdin.isatty():
            visibility = _prompt_visibility()
        else:
            visibility = "public"
    elif visibility is None:
        visibility = "public"

    if template:
        # Template mode — package entire .agent/ directory
        project_root = Path(path).resolve()

        if not _validate_before_publish(project_root):
            raise SystemExit(1)

        tarball = _publish_template_dir(
            project_root,
            output_dir,
            exclude_patterns=list(exclude) if exclude else None,
            include_memory=include_memory,
            include_all=include_all,
        )

        # Read name/version for display
        manifest_path = project_root / AGENT_DIR / MANIFEST_FILE
        with open(manifest_path) as f:
            mdata = yaml.safe_load(f) or {}
        tname = mdata.get("name", "unknown")
        tver = mdata.get("version", "0.0.0")

        console.print(f"[green]{t('publish.published_template')}[/] {tarball}")
        console.print(f"  {t('publish.name_version', name=tname, version=tver)}")
        console.print(f"  {t('publish.size', size=f'{tarball.stat().st_size / 1024:.1f}')}")

        # List what's excluded
        if not include_all:
            excluded = _TEMPLATE_DEFAULT_EXCLUDES.copy()
            if include_memory:
                excluded = [p for p in excluded if not p.startswith("memory")]
            if excluded:
                console.print(f"  {t('publish.excluded', patterns=', '.join(excluded))}")

        if registry:
            _upload_to_registry(
                tarball, tname, tver,
                mdata.get("description", ""),
                mdata.get("tags"),
                pkg_type="template",
                visibility=visibility,
            )
        else:
            console.print()
            console.print(f"[dim]{t('publish.use_registry')}[/]")
        return

    if skill_path:
        # Explicit directory — original behavior
        tarball = _publish_skill_dir(Path(skill_path).resolve(), output_dir)

        with open(tarball, "rb") as _f:
            pass  # just for size stat
        with tarfile.open(tarball, "r:gz") as tar:
            members = tar.getnames()

        # Read back id/version for display
        manifests = list(Path(skill_path).resolve().glob("*.skill.yaml")) + \
                    list(Path(skill_path).resolve().glob("skill.yaml"))
        if manifests:
            with open(manifests[0]) as f:
                mdata = yaml.safe_load(f)
            sid = mdata.get("id", "unknown")
            sver = mdata.get("version", "0.0.0")
        else:
            sid, sver = "unknown", "0.0.0"

        console.print(f"[green]{t('publish.published')}[/] {tarball}")
        console.print(f"  {t('publish.skill_version', id=sid, version=sver)}")
        console.print(f"  {t('publish.size', size=f'{tarball.stat().st_size / 1024:.1f}')}")

        if registry:
            _upload_to_registry(tarball, sid, sver, mdata.get("description", ""), mdata.get("tags"),
                                visibility=visibility)
        else:
            console.print()
            console.print(f"[dim]{t('publish.use_registry')}[/]")
    else:
        # Publish from agent.yaml
        project_root = Path(path).resolve()
        count = _publish_from_manifest(project_root, output_dir, skill)
        if count:
            console.print()
            console.print(f"[green]{t('publish.published_count', count=count, dir=output_dir)}[/]")

            if registry:
                _upload_tarballs_from_dir(output_dir, project_root, skill, visibility=visibility)
