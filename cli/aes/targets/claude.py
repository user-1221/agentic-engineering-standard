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
    compile_lifecycle_to_hooks_json,
    compose_instincts_section,
    compose_instructions_with_skill_index,
    format_skill_permissions,
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
            skill_runbooks=ctx.skill_runbooks,
        )

        if ctx.permissions:
            confirm_section = _build_confirm_section(ctx.permissions)
            if confirm_section:
                content += "\n" + confirm_section

        # Learned patterns from active instincts
        if ctx.active_instincts:
            fmt = "compact"
            if ctx.learning_config:
                fmt = (
                    ctx.learning_config.get("context_loading", {})
                    .get("format", "compact")
                )
            instincts_md = compose_instincts_section(ctx.active_instincts, fmt)
            if instincts_md:
                content += "\n" + instincts_md

        # Memory management instruction — only if /memory command exists
        has_memory_cmd = any(
            cmd.get("id") == "memory" for cmd in ctx.commands
        )
        if has_memory_cmd:
            content += (
                "\n## Memory Management\n\n"
                "At the end of significant work sessions \u2014 especially after "
                "completing commands, making architectural decisions, or solving "
                "difficult bugs \u2014 run `/memory` to persist learnings to "
                "`.agent/memory/`.\n"
            )

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
            cmd_id = cmd['id'].replace("/", "-").replace("\\", "-")
            rel_path = f".claude/commands/{cmd_id}.md"
            cmd_content = AES_SENTINEL_MD + "\n" + cmd.get("content", "")
            action = self._check_conflict(ctx.project_root, rel_path, force)
            plan.files.append(GeneratedFile(
                relative_path=rel_path,
                content=cmd_content,
                description=f"Claude slash command: /{cmd['id']}",
                action=action,
            ))

        # 4. .claude/hooks.json — lifecycle hooks
        if ctx.lifecycle:
            hooks_data = compile_lifecycle_to_hooks_json(ctx.lifecycle)
            if hooks_data.get("hooks"):
                hooks_data[AES_SENTINEL_JSON_KEY] = True
                hooks_json = json.dumps(hooks_data, indent=2) + "\n"
                action = self._check_conflict(
                    ctx.project_root, ".claude/hooks.json", force
                )
                plan.files.append(GeneratedFile(
                    relative_path=".claude/hooks.json",
                    content=hooks_json,
                    description="Claude Code lifecycle hooks",
                    action=action,
                ))

        # 5. .claude/rules/{category}/{file}.md — coding conventions
        if ctx.rules_files:
            for key, rule_content in ctx.rules_files.items():
                rel_path = f".claude/rules/{key}"
                full_content = AES_SENTINEL_MD + "\n" + rule_content
                action = self._check_conflict(
                    ctx.project_root, rel_path, force
                )
                plan.files.append(GeneratedFile(
                    relative_path=rel_path,
                    content=full_content,
                    description=f"Rule: {key}",
                    action=action,
                ))

        # 6. .claude/commands/skills/<id>.md (skill runbooks as slash commands)
        for skill_id, runbook in ctx.skill_runbooks.items():
            safe_id = skill_id.replace("/", "-").replace("\\", "-")
            rel_path = f".claude/commands/skills/{safe_id}.md"
            skill_content = AES_SENTINEL_MD + "\n" + runbook

            # Append per-skill metadata (negative triggers, permissions)
            meta = ctx.skill_metadata.get(skill_id, {})
            neg_triggers = meta.get("negative_triggers", [])
            allowed_tools = meta.get("allowed_tools")

            extras: List[str] = []
            if neg_triggers:
                extras.append("\n## Do NOT Use When\n")
                for trigger in neg_triggers:
                    extras.append(f"- {trigger}")
            perms_section = format_skill_permissions(allowed_tools)
            if perms_section:
                extras.append(f"\n## Skill Permissions\n\n{perms_section}")
            if extras:
                skill_content += "\n" + "\n".join(extras) + "\n"

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
