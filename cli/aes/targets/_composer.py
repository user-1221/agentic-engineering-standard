"""Shared composition logic for sync targets."""

from __future__ import annotations

from typing import Dict, List, Optional


def compose_instructions(
    project_name: str,
    instructions: Optional[str],
    orchestrator: Optional[str],
    skill_runbooks: Dict[str, str],
    memory_project: Optional[str],
    header: str,
) -> str:
    """Compose a single instructions document from .agent/ contents.

    Structure:
      1. Header (sentinel + title)
      2. instructions.md
      3. ORCHESTRATOR.md
      4. Skill runbooks
      5. memory/project.md
    """
    sections: List[str] = [header]

    if instructions:
        sections.append(instructions)

    if orchestrator:
        sections.append("---\n")
        sections.append(orchestrator)

    if skill_runbooks:
        sections.append("---\n")
        sections.append("# Skills Reference\n")
        for _skill_id, runbook in skill_runbooks.items():
            sections.append(runbook)

    if memory_project:
        sections.append("---\n")
        sections.append(memory_project)

    return "\n\n".join(sections) + "\n"


def translate_permissions_to_claude(permissions: dict) -> dict:
    """Translate AES permissions.yaml into Claude settings.local.json format.

    Claude permissions use patterns like:
      - Bash(git status*) for shell commands
      - Read(*) for file reading
      - Write(src/**) / Edit(src/**) for file writing
    """
    allowed: List[str] = []
    denied: List[str] = []

    # --- allow section ---
    allow = permissions.get("allow", {})

    allow_shell = allow.get("shell", {})
    if isinstance(allow_shell, dict):
        for category in ("read", "execute", "remote"):
            for pattern in _normalize_patterns(allow_shell.get(category)):
                allowed.append(f"Bash({pattern})")
    elif isinstance(allow_shell, list):
        for pattern in allow_shell:
            allowed.append(f"Bash({pattern})")

    allow_files = allow.get("files", {})
    for p in _normalize_patterns(allow_files.get("read")):
        allowed.append(f"Read({p})")
    for p in _normalize_patterns(allow_files.get("write")):
        allowed.append(f"Write({p})")
        allowed.append(f"Edit({p})")
    for p in _normalize_patterns(allow_files.get("create")):
        allowed.append(f"Write({p})")

    # --- deny section ---
    deny = permissions.get("deny", {})

    deny_shell = deny.get("shell", {})
    if isinstance(deny_shell, list):
        for pattern in deny_shell:
            denied.append(f"Bash({pattern})")
    elif isinstance(deny_shell, dict):
        for category in ("read", "execute", "remote"):
            for pattern in _normalize_patterns(deny_shell.get(category)):
                denied.append(f"Bash({pattern})")

    deny_files = deny.get("files", {})
    for p in _normalize_patterns(deny_files.get("write")):
        denied.append(f"Write({p})")
        denied.append(f"Edit({p})")
    for p in _normalize_patterns(deny_files.get("delete")):
        denied.append(f"Write({p})")

    # --- overrides escape hatch ---
    overrides = permissions.get("overrides", {}).get("claude", {})
    override_perms = overrides.get("permissions", {})
    if override_perms.get("allow"):
        allowed.extend(override_perms["allow"])
    if override_perms.get("deny"):
        denied.extend(override_perms["deny"])

    result: dict = {"permissions": {}}
    if allowed:
        result["permissions"]["allow"] = sorted(set(allowed))
    if denied:
        result["permissions"]["deny"] = sorted(set(denied))

    return result


def _normalize_patterns(value: object) -> List[str]:
    """Normalize a single pattern or list of patterns to a list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    return []
