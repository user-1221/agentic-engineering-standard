"""Cursor sync target."""

from __future__ import annotations

from aes.targets._base import AES_SENTINEL_MD, AgentContext, GeneratedFile, SyncPlan, SyncTarget
from aes.targets._composer import (
    compose_instincts_section,
    compose_instructions,
    compose_rules_section,
    translate_permissions_to_markdown,
)


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
            perms_md = translate_permissions_to_markdown(ctx.permissions)
            if perms_md:
                content += "\n" + perms_md

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

        # Coding conventions
        if ctx.rules_files:
            rules_md = compose_rules_section(ctx.rules_files)
            if rules_md:
                content += "\n" + rules_md

        action = self._check_conflict(ctx.project_root, ".cursorrules", force)
        plan.files.append(GeneratedFile(
            relative_path=".cursorrules",
            content=content,
            description="Cursor rules file",
            action=action,
        ))

        return plan
