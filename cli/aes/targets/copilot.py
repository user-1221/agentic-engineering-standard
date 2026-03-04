"""GitHub Copilot sync target."""

from __future__ import annotations

from aes.targets._base import AES_SENTINEL_MD, AgentContext, GeneratedFile, SyncPlan, SyncTarget
from aes.targets._composer import compose_instructions


class CopilotTarget(SyncTarget):

    @property
    def name(self) -> str:
        return "copilot"

    def plan(self, ctx: AgentContext, force: bool) -> SyncPlan:
        plan = SyncPlan(target_name=self.name)

        header = (
            AES_SENTINEL_MD
            + "\n# "
            + ctx.manifest.get("name", "Project")
            + " \u2014 Copilot Instructions"
        )
        content = compose_instructions(
            project_name=ctx.manifest.get("name", "Project"),
            instructions=ctx.instructions,
            orchestrator=ctx.orchestrator,
            skill_runbooks=ctx.skill_runbooks,
            memory_project=ctx.memory_project,
            header=header,
        )

        action = self._check_conflict(
            ctx.project_root, ".github/copilot-instructions.md", force
        )
        plan.files.append(GeneratedFile(
            relative_path=".github/copilot-instructions.md",
            content=content,
            description="GitHub Copilot instructions",
            action=action,
        ))

        return plan
