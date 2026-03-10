"""Shared composition logic for sync targets."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


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


def compose_instructions_with_skill_index(
    project_name: str,
    instructions: Optional[str],
    orchestrator: Optional[str],
    skill_metadata: Dict[str, Dict[str, Any]],
    memory_project: Optional[str],
    header: str,
    skill_runbooks: Optional[Dict[str, str]] = None,
) -> str:
    """Compose instructions with a skill index instead of inlined runbooks.

    Skills are synced as separate command files; this just lists them
    so the agent knows they exist and can be invoked as slash commands.

    Skills with ``activation: auto`` have their description (and optionally
    a runbook summary) inlined directly so the agent can match them without
    invoking a slash command.  ``hybrid`` skills appear in both sections.
    """
    sections: List[str] = [header]

    if instructions:
        sections.append(instructions)

    if orchestrator:
        sections.append("---\n")
        sections.append(orchestrator)

    if skill_metadata:
        # Partition skills by activation mode
        auto_skills: Dict[str, Dict[str, Any]] = {}
        explicit_skills: Dict[str, Dict[str, Any]] = {}
        for skill_id, meta in skill_metadata.items():
            mode = meta.get("activation", "explicit")
            if mode in ("auto", "hybrid"):
                auto_skills[skill_id] = meta
            if mode in ("explicit", "hybrid"):
                explicit_skills[skill_id] = meta

        # Auto-activated skills — inlined into instructions
        if auto_skills:
            sections.append("---\n")
            auto_lines: List[str] = [
                "# Auto-Activated Skills\n",
                "The following skills activate automatically based on context:\n",
            ]
            for skill_id, meta in auto_skills.items():
                name = meta.get("name", skill_id)
                desc = meta.get("description", "")
                neg = meta.get("negative_triggers", [])
                auto_lines.append(f"### {name} (`/skills/{skill_id}`)\n")
                if desc:
                    auto_lines.append(desc)
                if neg:
                    auto_lines.append("")
                    for trigger in neg:
                        auto_lines.append(f"- {trigger}")
                perms = format_skill_permissions(meta.get("allowed_tools"))
                if perms:
                    auto_lines.append("")
                    auto_lines.append(perms)
                auto_lines.append("")
            sections.append("\n".join(auto_lines))

        # Explicit skills — listed as slash commands
        if explicit_skills:
            sections.append("---\n")
            lines: List[str] = [
                "# Available Skills\n",
                "The following skills are available as slash commands:\n",
            ]
            for skill_id, meta in explicit_skills.items():
                name = meta.get("name", skill_id)
                desc = meta.get("description", "")
                neg = meta.get("negative_triggers", [])
                line = f"- **/skills/{skill_id}** — {name}"
                if desc:
                    line += f": {desc}"
                if neg:
                    line += " " + " ".join(f"[{t}]" for t in neg)
                lines.append(line)
            sections.append("\n".join(lines))

    if memory_project:
        sections.append("---\n")
        sections.append(memory_project)

    return "\n\n".join(sections) + "\n"


def format_skill_permissions(allowed_tools: Optional[Dict[str, Any]]) -> str:
    """Format per-skill allowed_tools as a markdown permissions note.

    Returns empty string if no permissions are specified.
    """
    if not allowed_tools:
        return ""

    parts: List[str] = ["**Permissions:**"]

    shell = allowed_tools.get("shell")
    if shell is not None:
        parts.append(f"- Shell: {'allowed' if shell else 'denied'}")

    files = allowed_tools.get("files")
    if isinstance(files, dict):
        read_val = files.get("read")
        write_val = files.get("write")
        if read_val is not None:
            if isinstance(read_val, bool):
                parts.append(f"- File read: {'allowed' if read_val else 'denied'}")
            elif isinstance(read_val, list):
                parts.append(f"- File read: {', '.join(f'`{p}`' for p in read_val)}")
        if write_val is not None:
            if isinstance(write_val, bool):
                parts.append(f"- File write: {'allowed' if write_val else 'denied'}")
            elif isinstance(write_val, list):
                parts.append(f"- File write: {', '.join(f'`{p}`' for p in write_val)}")

    network = allowed_tools.get("network")
    if network is not None:
        parts.append(f"- Network: {'allowed' if network else 'denied'}")

    mcp = allowed_tools.get("mcp_servers")
    if mcp:
        parts.append(f"- MCP servers: {', '.join(mcp)}")

    if len(parts) <= 1:
        return ""

    return "\n".join(parts)


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


def translate_permissions_to_markdown(permissions: dict) -> str:
    """Translate AES permissions.yaml into a markdown restrictions section.

    Used by Cursor, Copilot, and Windsurf targets which don't have structured
    permission formats — they rely on markdown instructions instead.
    """
    sections: List[str] = []

    # --- Allow: file scope ---
    allow = permissions.get("allow", {})
    allow_files = allow.get("files", {})
    write_patterns = _normalize_patterns(allow_files.get("write"))
    if write_patterns:
        sections.append("### File Scope\n")
        sections.append("Focus edits on these directories/patterns:\n")
        for p in write_patterns:
            sections.append(f"- `{p}`")
        sections.append("")

    # --- Allow: shell commands ---
    allow_shell = allow.get("shell", {})
    allowed_cmds: List[str] = []
    if isinstance(allow_shell, dict):
        for category in ("read", "execute", "remote"):
            allowed_cmds.extend(_normalize_patterns(allow_shell.get(category)))
    elif isinstance(allow_shell, list):
        allowed_cmds.extend(allow_shell)
    if allowed_cmds:
        sections.append("### Allowed Commands\n")
        for cmd in allowed_cmds:
            sections.append(f"- `{cmd}`")
        sections.append("")

    # --- Deny ---
    deny = permissions.get("deny", {})
    deny_shell = deny.get("shell", [])
    deny_cmds: List[str] = []
    if isinstance(deny_shell, list):
        deny_cmds.extend(deny_shell)
    elif isinstance(deny_shell, dict):
        for category in ("read", "execute", "remote"):
            deny_cmds.extend(_normalize_patterns(deny_shell.get(category)))

    deny_files = deny.get("files", {})
    deny_write = _normalize_patterns(deny_files.get("write"))
    deny_delete = _normalize_patterns(deny_files.get("delete"))

    if deny_cmds or deny_write or deny_delete:
        sections.append("### Never Do These\n")
        for cmd in deny_cmds:
            sections.append(f"- Never run: `{cmd}`")
        for p in deny_write:
            sections.append(f"- Never write to: `{p}`")
        for p in deny_delete:
            sections.append(f"- Never delete: `{p}`")
        sections.append("")

    # --- Confirm ---
    confirm = permissions.get("confirm", {})
    confirm_shell = confirm.get("shell", [])
    confirm_actions = confirm.get("actions", [])
    if confirm_shell or confirm_actions:
        sections.append("### Ask Before Running\n")
        for cmd in (confirm_shell if isinstance(confirm_shell, list) else []):
            sections.append(f"- `{cmd}`")
        for action in (confirm_actions if isinstance(confirm_actions, list) else []):
            sections.append(f"- Action: {action}")
        sections.append("")

    # --- Resource limits ---
    resource_limits = permissions.get("resource_limits", {})
    if resource_limits:
        sections.append("### Resource Limits\n")
        for key, val in resource_limits.items():
            sections.append(f"- {key}: {val}")
        sections.append("")

    if not sections:
        return ""

    return "\n## Permissions\n\n" + "\n".join(sections) + "\n"


def _normalize_patterns(value: object) -> List[str]:
    """Normalize a single pattern or list of patterns to a list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    return []
