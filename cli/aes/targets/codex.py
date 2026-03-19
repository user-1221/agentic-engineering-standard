"""OpenAI Codex CLI sync target."""

from __future__ import annotations

from typing import List

from aes.targets._base import (
    AES_SENTINEL_MD,
    AgentContext,
    GeneratedFile,
    SyncPlan,
    SyncTarget,
)
from aes.targets._composer import (
    compose_instincts_section,
    compose_instructions_with_skill_index,
    compose_lifecycle_to_markdown,
    compose_rules_section,
    format_skill_permissions,
    merge_skill_to_skillmd,
    translate_permissions_to_markdown,
)


class CodexTarget(SyncTarget):

    @property
    def name(self) -> str:
        return "codex"

    def plan(self, ctx: AgentContext, force: bool) -> SyncPlan:
        plan = SyncPlan(target_name=self.name)

        # 1. AGENTS.md — skill index (Codex discovers skills natively)
        header = (
            AES_SENTINEL_MD
            + "\n# "
            + ctx.manifest.get("name", "Project")
            + " — Agent Instructions"
        )
        content = compose_instructions_with_skill_index(
            project_name=ctx.manifest.get("name", "Project"),
            instructions=ctx.instructions,
            orchestrator=ctx.orchestrator,
            skill_metadata=ctx.skill_metadata,
            memory_project=ctx.memory_project,
            header=header,
            skill_runbooks=ctx.skill_runbooks,
            skill_path_prefix=".agents/skills",
        )

        if ctx.permissions:
            perms_md = translate_permissions_to_markdown(ctx.permissions)
            if perms_md:
                content += "\n" + perms_md

        # Lifecycle hooks (lossy — behavioral instructions)
        if ctx.lifecycle:
            lc_md = compose_lifecycle_to_markdown(ctx.lifecycle)
            if lc_md:
                content += "\n" + lc_md

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

        action = self._check_conflict(ctx.project_root, "AGENTS.md", force)
        plan.files.append(GeneratedFile(
            relative_path="AGENTS.md",
            content=content,
            description="Agent instructions for Codex CLI",
            action=action,
        ))

        # 2. .agents/skills/<id>/SKILL.md — per-skill files
        for skill_id, runbook in ctx.skill_runbooks.items():
            safe_id = skill_id.replace("/", "-").replace("\\", "-")
            rel_path = f".agents/skills/{safe_id}/SKILL.md"
            meta = ctx.skill_metadata.get(skill_id, {})

            # Build full body: runbook + negative triggers + permissions
            body_parts: List[str] = [runbook.strip()] if runbook.strip() else []

            neg_triggers = meta.get("negative_triggers", [])
            if neg_triggers:
                lines = ["\n## Do NOT Use When\n"]
                for trigger in neg_triggers:
                    lines.append(f"- {trigger}")
                body_parts.append("\n".join(lines))

            perms_section = format_skill_permissions(meta.get("allowed_tools"))
            if perms_section:
                body_parts.append(f"\n## Skill Permissions\n\n{perms_section}")

            full_body = "\n".join(body_parts) if body_parts else ""

            skill_content = AES_SENTINEL_MD + "\n" + merge_skill_to_skillmd(
                skill_id=skill_id,
                metadata=meta,
                runbook=full_body,
            )

            action = self._check_conflict(ctx.project_root, rel_path, force)
            plan.files.append(GeneratedFile(
                relative_path=rel_path,
                content=skill_content,
                description=f"Codex skill: {skill_id}",
                action=action,
            ))

        return plan
