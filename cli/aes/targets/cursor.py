"""Cursor sync target."""

from __future__ import annotations

from typing import List

from aes.targets._base import AES_SENTINEL_MD, AgentContext, GeneratedFile, SyncPlan, SyncTarget
from aes.targets._composer import compose_instructions


class CursorTarget(SyncTarget):

    @property
    def name(self) -> str:
        return "cursor"

    def plan(self, ctx: AgentContext, force: bool) -> SyncPlan:
        plan = SyncPlan(target_name=self.name)

        header = (
            AES_SENTINEL_MD
            + "\n# "
            + ctx.manifest.get("name", "Project")
            + " \u2014 Cursor Rules"
        )
        content = compose_instructions(
            project_name=ctx.manifest.get("name", "Project"),
            instructions=ctx.instructions,
            orchestrator=ctx.orchestrator,
            skill_runbooks=ctx.skill_runbooks,
            memory_project=ctx.memory_project,
            header=header,
        )

        if ctx.permissions:
            deny_section = _build_deny_section(ctx.permissions)
            if deny_section:
                content += "\n" + deny_section

        action = self._check_conflict(ctx.project_root, ".cursorrules", force)
        plan.files.append(GeneratedFile(
            relative_path=".cursorrules",
            content=content,
            description="Cursor rules file",
            action=action,
        ))

        return plan


def _build_deny_section(permissions: dict) -> str:
    """Build a markdown section with deny/confirm rules for Cursor."""
    deny = permissions.get("deny", {})
    confirm = permissions.get("confirm", {})
    if not deny and not confirm:
        return ""

    lines: List[str] = ["\n## Restrictions\n"]

    deny_shell = deny.get("shell", [])
    if isinstance(deny_shell, list) and deny_shell:
        lines.append("### Never Run These Commands\n")
        for cmd in deny_shell:
            lines.append(f"- `{cmd}`")
        lines.append("")

    confirm_shell = confirm.get("shell", [])
    if confirm_shell:
        lines.append("### Ask Before Running\n")
        for cmd in confirm_shell:
            lines.append(f"- `{cmd}`")
        lines.append("")

    return "\n".join(lines) + "\n"
