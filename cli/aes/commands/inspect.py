"""aes inspect — Show project structure and stats."""

from __future__ import annotations

import tarfile
import tempfile
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.table import Table

from aes.config import AGENT_DIR, BOM_FILE, DECISIONS_DIR
from aes.i18n import t
from aes.registry import (
    fetch_index,
    download_package,
    parse_registry_source,
    resolve_version,
    _parse_version,
)
from aes.commands.install import _safe_extract

console = Console()


def _load_yaml(path: Path) -> dict:
    """Load YAML file, return empty dict on error."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _render_workflow_diagram(workflow: dict) -> str:
    """Render a simple ASCII state diagram from a workflow definition."""
    states = workflow.get("states", {})
    transitions = workflow.get("transitions", [])

    if not states or not transitions:
        return f"  ({t('inspect.no_states')})"

    lines = []
    # Find initial and terminal states
    initial = [s for s, v in states.items() if v.get("initial")]
    terminal = [s for s, v in states.items() if v.get("terminal")]
    intermediate = [s for s in states if s not in initial and s not in terminal]

    # Render flow
    all_ordered = initial + intermediate + terminal
    if all_ordered:
        # Build transition map
        tx_map: dict[str, list[str]] = {}
        for tx in transitions:
            src = tx.get("from", "")
            dst = tx.get("to", "")
            tx_map.setdefault(src, []).append(dst)

        # Show forward transitions
        forward_chain = initial.copy()
        visited = set(initial)
        current = initial[0] if initial else ""
        while current:
            targets = tx_map.get(current, [])
            next_state = None
            for tgt in targets:
                if tgt not in visited and tgt not in terminal:
                    next_state = tgt
                    break
            if next_state:
                forward_chain.append(next_state)
                visited.add(next_state)
                current = next_state
            else:
                break

        lines.append("  " + " --> ".join(forward_chain))
        if terminal:
            lines.append(f"  {t('inspect.terminal', states=', '.join(terminal))}")

        # Show backward transitions
        backward = [tx for tx in transitions if tx.get("to") in visited and
                     all_ordered.index(tx.get("from", "")) > all_ordered.index(tx.get("to", ""))
                     if tx.get("from", "") in all_ordered and tx.get("to", "") in all_ordered]
        for tx in backward:
            lines.append(f"  (loop) {tx['from']} --> {tx['to']}: {tx.get('description', 'reframe')}")

    return "\n".join(lines) if lines else f"  ({t('inspect.no_states')})"


def _is_local_path(target: str) -> bool:
    """Return True if target looks like a local filesystem path."""
    if target.startswith(("/", "./", "../")):
        return True
    if Path(target).is_dir():
        return True
    return False


def _inspect_local(path: str) -> None:
    """Inspect a local .agent/ directory."""
    project_root = Path(path).resolve()
    agent_dir = project_root / AGENT_DIR

    if not agent_dir.exists():
        console.print(f"[red]{t('common.error')}:[/] {t('common.no_agent_dir', agent_dir=AGENT_DIR, path=project_root)}")
        raise SystemExit(1)

    manifest_path = agent_dir / "agent.yaml"
    if not manifest_path.exists():
        console.print(f"[red]{t('common.error')}:[/] {t('common.no_manifest', manifest='agent.yaml', agent_dir=agent_dir)}")
        raise SystemExit(1)

    manifest = _load_yaml(manifest_path)

    # Header
    console.print()
    console.print(f"[bold]{manifest.get('name', 'unknown')}[/] v{manifest.get('version', '?')}")
    console.print(f"  {manifest.get('description', '')}")
    console.print(f"  {t('inspect.domain', domain=manifest.get('domain', 'unspecified'))} | "
                  f"{t('inspect.language', language=manifest.get('runtime', {}).get('language', '?'))} | "
                  f"{t('inspect.aes_version', version=manifest.get('aes', '?'))}")
    console.print()

    # Skills table
    skills = manifest.get("skills", [])
    if skills:
        table = Table(title=t("inspect.skills_table"), show_header=True, header_style="bold")
        table.add_column(t("inspect.col_id"), style="cyan")
        table.add_column(t("inspect.col_manifest"))
        table.add_column(t("inspect.col_runbook"))
        table.add_column(t("inspect.col_status"))

        for skill in skills:
            manifest_exists = (agent_dir / skill.get("manifest", "")).exists() if skill.get("manifest") else False
            runbook_exists = (agent_dir / skill.get("runbook", "")).exists() if skill.get("runbook") else False
            status = f"[green]{t('inspect.ok')}[/]" if manifest_exists and runbook_exists else f"[red]{t('inspect.missing')}[/]"
            table.add_row(
                skill.get("id", "?"),
                skill.get("manifest", "-"),
                skill.get("runbook", "-"),
                status,
            )
        console.print(table)
        console.print()

    # Registries
    registries = manifest.get("registries", [])
    if registries:
        table = Table(title=t("inspect.registries_table"), show_header=True, header_style="bold")
        table.add_column(t("inspect.col_id"), style="cyan")
        table.add_column(t("inspect.col_path"))
        table.add_column(t("inspect.col_description"))
        table.add_column(t("inspect.col_entries"))

        for reg in registries:
            reg_path = agent_dir / reg["path"]
            entry_count = "?"
            if reg_path.exists():
                reg_data = _load_yaml(reg_path)
                categories = reg_data.get("categories", {})
                count = sum(
                    len(v) if isinstance(v, dict) else 0
                    for v in categories.values()
                )
                entry_count = str(count)

            table.add_row(
                reg.get("id", "?"),
                reg["path"],
                reg.get("description", "-"),
                entry_count,
            )
        console.print(table)
        console.print()

    # Workflows
    workflows = manifest.get("workflows", [])
    if workflows:
        for wf_ref in workflows:
            wf_path = agent_dir / wf_ref["path"]
            if wf_path.exists():
                wf_data = _load_yaml(wf_path)
                n_states = len(wf_data.get("states", {}))
                n_transitions = len(wf_data.get("transitions", []))
                console.print(f"[bold]{t('inspect.workflow')}[/] {wf_ref['id']} ({n_states} states, {n_transitions} transitions)")
                console.print(_render_workflow_diagram(wf_data))
                console.print()

    # Commands
    commands = manifest.get("commands", [])
    if commands:
        table = Table(title=t("inspect.commands_table"), show_header=True, header_style="bold")
        table.add_column(t("inspect.col_trigger"), style="cyan")
        table.add_column(t("inspect.col_description"))
        for cmd in commands:
            table.add_row(
                cmd.get("trigger", f"/{cmd.get('id', '?')}"),
                cmd.get("description", "-"),
            )
        console.print(table)
        console.print()

    # Models
    models = manifest.get("models", [])
    if models:
        console.print(f"[bold]{t('inspect.models_section')}[/]")
        for m in models:
            purpose = m.get("purpose", "")
            purpose_str = f" [dim]({purpose})[/]" if purpose else ""
            console.print(f"  {m.get('name', '?')} — {m.get('provider', '?')}{purpose_str}")
        console.print()

    # Provenance
    provenance = manifest.get("provenance", {})
    if provenance:
        console.print(f"[bold]{t('inspect.provenance_section')}[/]")
        if provenance.get("created_by"):
            console.print(f"  {t('inspect.provenance_created_by', value=provenance['created_by'])}")
        if provenance.get("source"):
            console.print(f"  {t('inspect.provenance_source', value=provenance['source'])}")
        console.print()

    # BOM summary
    bom_path = agent_dir / BOM_FILE
    if bom_path.exists():
        bom = _load_yaml(bom_path)
        n_models = len(bom.get("models", []))
        n_frameworks = len(bom.get("frameworks", []))
        n_tools = len(bom.get("tools", []))
        n_data = len(bom.get("data_sources", []))
        console.print(f"[bold]{t('inspect.bom_section')}[/]")
        console.print(f"  {t('inspect.bom_summary', models=n_models, frameworks=n_frameworks, tools=n_tools, data=n_data)}")
        console.print()

    # Decision records count
    decisions_dir = agent_dir / DECISIONS_DIR
    if decisions_dir.exists() and decisions_dir.is_dir():
        dr_count = len(list(decisions_dir.glob("*.yaml")))
        if dr_count > 0:
            console.print(f"[bold]{t('inspect.decisions_section')}[/]")
            console.print(f"  {t('inspect.decisions_count', count=dr_count)}")
            console.print()

    # Summary
    console.print(f"[bold]{t('inspect.summary')}[/]")
    console.print(f"  {t('inspect.skills_count', count=len(skills))}")
    console.print(f"  {t('inspect.registries_count', count=len(registries))}")
    console.print(f"  {t('inspect.workflows_count', count=len(workflows))}")
    console.print(f"  {t('inspect.commands_count', count=len(commands))}")

    # Resources
    resources = manifest.get("resources", {})
    if resources:
        console.print(f"  {t('inspect.cpu_limit', value=resources.get('max_cpu_percent', '-'))}")
        console.print(f"  {t('inspect.mem_limit', value=resources.get('max_memory_percent', '-'))}")
    console.print()


# ---------------------------------------------------------------------------
# Remote registry inspection
# ---------------------------------------------------------------------------

def _render_registry_metadata(name: str, pkg: dict, selected_version: str) -> None:
    """Render registry-level metadata for a package."""
    console.print()
    console.print(f"[bold]{name}[/] v{selected_version}  [dim]({t('inspect.registry_label')})[/]")
    console.print(f"  {pkg.get('description', '')}")
    console.print(f"  {t('inspect.type_label', type=pkg.get('type', 'skill'))} | "
                  f"{t('inspect.visibility_label', visibility=pkg.get('visibility', 'public'))}")

    tags = pkg.get("tags", [])
    if tags:
        console.print(f"  {t('inspect.tags_label', tags=', '.join(tags))}")
    console.print()

    # Versions table
    versions_dict = pkg.get("versions", {})
    if versions_dict:
        table = Table(title=t("inspect.versions_table"), show_header=True, header_style="bold")
        table.add_column(t("inspect.col_version"), style="cyan")
        table.add_column(t("inspect.col_published"))
        table.add_column(t("inspect.col_sha256"), style="dim")

        sorted_versions = sorted(
            versions_dict.items(),
            key=lambda kv: _parse_version(kv[0]),
            reverse=True,
        )

        for ver, info in sorted_versions:
            marker = f" [bold green]({t('inspect.latest')})[/]" if ver == pkg.get("latest") else ""
            published = info.get("published_at", "?")
            if isinstance(published, str) and "T" in published:
                published = published.split("T")[0]
            sha_short = info.get("sha256", "?")[:12] + "..."
            table.add_row(f"{ver}{marker}", published, sha_short)

        console.print(table)
        console.print()


def _inspect_remote_skill(extract_dir: Path) -> None:
    """Render skill manifest details from an extracted package."""
    manifests = list(extract_dir.rglob("*.skill.yaml"))
    if not manifests:
        manifests = list(extract_dir.rglob("skill.yaml"))
    if not manifests:
        console.print(f"[dim]{t('inspect.no_skill_manifest')}[/]")
        return

    manifest = _load_yaml(manifests[0])

    console.print(f"[bold]{t('inspect.skill_details')}[/]")
    console.print(f"  {t('inspect.field_id', value=manifest.get('id', '?'))}")
    console.print(f"  {t('inspect.field_name', value=manifest.get('name', '?'))}")
    console.print(f"  {t('inspect.field_version', value=manifest.get('version', '?'))}")
    console.print(f"  {t('inspect.field_description', value=manifest.get('description', ''))}")
    console.print()

    # Inputs
    inputs = manifest.get("inputs", {})
    required = inputs.get("required", [])
    optional = inputs.get("optional", [])
    env_inputs = inputs.get("environment", [])

    if required or optional:
        table = Table(title=t("inspect.inputs_table"), show_header=True, header_style="bold")
        table.add_column(t("search.col_name"), style="cyan")
        table.add_column(t("search.col_type"))
        table.add_column(t("inspect.col_required"))
        table.add_column(t("search.col_description"))

        for inp in required:
            table.add_row(
                inp.get("name", "?"),
                inp.get("type", "?"),
                f"[green]{t('inspect.yes')}[/]",
                inp.get("description", ""),
            )
        for inp in optional:
            table.add_row(
                inp.get("name", "?"),
                inp.get("type", "?"),
                t("inspect.no"),
                inp.get("description", ""),
            )
        console.print(table)
        console.print()

    if env_inputs:
        console.print(f"  {t('inspect.environment', vars=', '.join(env_inputs))}")
        console.print()

    # Outputs
    outputs = manifest.get("outputs", [])
    if outputs:
        table = Table(title=t("inspect.outputs_table"), show_header=True, header_style="bold")
        table.add_column(t("search.col_name"), style="cyan")
        table.add_column(t("search.col_type"))
        table.add_column(t("search.col_description"))

        for out in outputs:
            table.add_row(
                out.get("name", "?"),
                out.get("type", "?"),
                out.get("description", ""),
            )
        console.print(table)
        console.print()

    # Dependencies
    depends_on = manifest.get("depends_on", [])
    blocks = manifest.get("blocks", [])
    if depends_on or blocks:
        console.print(f"[bold]{t('inspect.dependencies')}[/]")
        if depends_on:
            console.print(f"  {t('inspect.depends_on', deps=', '.join(str(d) for d in depends_on))}")
        if blocks:
            console.print(f"  {t('inspect.blocks', deps=', '.join(str(b) for b in blocks))}")
        console.print()

    # Triggers
    triggers = manifest.get("triggers", [])
    if triggers:
        console.print(f"[bold]{t('inspect.triggers')}[/]")
        for trig in triggers:
            label = trig.get("command", trig.get("cron", trig.get("description", "")))
            console.print(f"  [{trig.get('type', '?')}] {label}")
        console.print()

    # Negative triggers
    neg_triggers = manifest.get("negative_triggers", [])
    if neg_triggers:
        console.print(f"[bold]{t('inspect.negative_triggers')}[/]")
        for nt in neg_triggers:
            console.print(f"  [red]- {nt}[/]")
        console.print()

    # Tags
    tags = manifest.get("tags", [])
    if tags:
        console.print(f"  {t('inspect.tags_label', tags=', '.join(tags))}")
        console.print()


def _inspect_remote_template(extract_dir: Path) -> None:
    """Render template details by finding .agent/ and reusing local inspect."""
    for candidate in extract_dir.rglob(AGENT_DIR):
        if candidate.is_dir() and (candidate / "agent.yaml").exists():
            project_root = candidate.parent
            _inspect_local(str(project_root))
            return

    console.print(f"[dim]{t('inspect.no_agent_in_template')}[/]")


def _inspect_remote(target: str) -> None:
    """Inspect a remote registry package."""
    try:
        name, version_spec = parse_registry_source(target)
    except ValueError as exc:
        console.print(f"[red]{t('common.error')}:[/] {exc}")
        raise SystemExit(1)

    try:
        index = fetch_index()
    except Exception as exc:
        console.print(f"[red]{t('common.error')}:[/] {t('search.fetch_failed', exc=exc)}")
        console.print(f"[dim]{t('search.network_hint')}[/]")
        raise SystemExit(1)

    packages = index.get("packages", {})
    if name not in packages:
        console.print(f"[red]{t('common.error')}:[/] {t('inspect.package_not_found', name=name)}")
        console.print(f"[dim]{t('inspect.use_search_hint')}[/]")
        raise SystemExit(1)

    pkg = packages[name]
    pkg_type = pkg.get("type", "skill")
    versions_dict = pkg.get("versions", {})

    available = list(versions_dict.keys())
    version = resolve_version(version_spec, available)
    if version is None:
        console.print(
            f"[red]{t('common.error')}:[/] {t('inspect.no_version_match', name=name, spec=version_spec, available=', '.join(available))}"
        )
        raise SystemExit(1)

    # Registry metadata
    _render_registry_metadata(name, pkg, version)

    # Download and inspect package contents
    version_info = versions_dict[version]
    sha256_expected = version_info.get("sha256", "")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        try:
            tarball = download_package(name, version, sha256_expected, tmp_dir)
        except Exception as exc:
            console.print(f"[yellow]{t('common.warning')}:[/] {t('inspect.download_warning', exc=exc)}")
            console.print(f"[dim]{t('inspect.metadata_only')}[/]")
            return

        with tarfile.open(tarball, "r:gz") as tar:
            _safe_extract(tar, tmp_dir)

        if pkg_type == "template":
            _inspect_remote_template(tmp_dir)
        else:
            _inspect_remote_skill(tmp_dir)


@click.command("inspect")
@click.argument("target", default=".")
def inspect_cmd(target: str) -> None:
    """Show AES project structure, or inspect a remote registry package.

    \b
    Local:   aes inspect ./my-project
    Remote:  aes inspect deploy
             aes inspect deploy@1.0.0
             aes inspect aes-hub/deploy
    """
    if _is_local_path(target):
        _inspect_local(target)
    else:
        _inspect_remote(target)
