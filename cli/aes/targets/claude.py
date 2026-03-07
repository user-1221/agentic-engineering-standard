"""Claude Code sync target."""

from __future__ import annotations

import json
from typing import List

from aes.targets._base import (
    AES_SENTINEL_JSON_KEY,
    AES_SENTINEL_MD,
    AgentContext,
    GeneratedFile,
    SyncPlan,
    SyncTarget,
)
from aes.targets._composer import (
    compose_instructions_with_skill_index,
    translate_permissions_to_claude,
)


class ClaudeTarget(SyncTarget):

    @property
    def name(self) -> str:
        return "claude"

    def plan(self, ctx: AgentContext, force: bool) -> SyncPlan:
        plan = SyncPlan(target_name=self.name)

        # 1. CLAUDE.md — with skill index (not inlined runbooks)
        header = (
            AES_SENTINEL_MD
            + "\n# "
            + ctx.manifest.get("name", "Project")
            + " \u2014 Agent Instructions"
        )
        content = compose_instructions_with_skill_index(
            project_name=ctx.manifest.get("name", "Project"),
            instructions=ctx.instructions,
            orchestrator=ctx.orchestrator,
            skill_metadata=ctx.skill_metadata,
            memory_project=ctx.memory_project,
            header=header,
        )

        if ctx.permissions:
            confirm_section = _build_confirm_section(ctx.permissions)
            if confirm_section:
                content += "\n" + confirm_section

        action = self._check_conflict(ctx.project_root, "CLAUDE.md", force)
        plan.files.append(GeneratedFile(
            relative_path="CLAUDE.md",
            content=content,
            description="Agent instructions for Claude Code",
            action=action,
        ))

        # 2. .claude/settings.local.json
        if ctx.permissions:
            settings = translate_permissions_to_claude(ctx.permissions)
            settings[AES_SENTINEL_JSON_KEY] = True
            settings_json = json.dumps(settings, indent=2) + "\n"

            action = self._check_conflict(
                ctx.project_root, ".claude/settings.local.json", force
            )
            plan.files.append(GeneratedFile(
                relative_path=".claude/settings.local.json",
                content=settings_json,
                description="Claude Code permissions",
                action=action,
            ))

        # 3. .claude/commands/*.md (user-defined commands)
        for cmd in ctx.commands:
            rel_path = f".claude/commands/{cmd['id']}.md"
            cmd_content = AES_SENTINEL_MD + "\n" + cmd.get("content", "")
            action = self._check_conflict(ctx.project_root, rel_path, force)
            plan.files.append(GeneratedFile(
                relative_path=rel_path,
                content=cmd_content,
                description=f"Claude slash command: /{cmd['id']}",
                action=action,
            ))

        # 4. .claude/commands/skills/<id>.md (skill runbooks as slash commands)
        for skill_id, runbook in ctx.skill_runbooks.items():
            rel_path = f".claude/commands/skills/{skill_id}.md"
            skill_content = AES_SENTINEL_MD + "\n" + runbook
            action = self._check_conflict(ctx.project_root, rel_path, force)
            plan.files.append(GeneratedFile(
                relative_path=rel_path,
                content=skill_content,
                description=f"Skill slash command: /skills/{skill_id}",
                action=action,
            ))

        return plan


def _build_confirm_section(permissions: dict) -> str:
    """Build a markdown section listing actions that require confirmation."""
    confirm = permissions.get("confirm", {})
    if not confirm:
        return ""

    lines: List[str] = [
        "\n## Actions Requiring Confirmation\n",
        "Always ask for explicit user approval before:\n",
    ]

    for cmd in confirm.get("shell", []):
        lines.append(f"- Running: `{cmd}`")

    for action in confirm.get("actions", []):
        lines.append(f"- Action: {action}")

    confirm_files = confirm.get("files", {})
    for p in _as_list(confirm_files.get("delete")):
        lines.append(f"- Deleting files matching: `{p}`")

    return "\n".join(lines) + "\n"


def _as_list(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    return []
