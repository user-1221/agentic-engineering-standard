"""OpenClaw sync target — generates .openclaw/ directory tree."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import click
import yaml

from aes.targets._base import (
    AES_SENTINEL_JSON_KEY,
    AES_SENTINEL_MD,
    AgentContext,
    GeneratedFile,
    SyncPlan,
    SyncTarget,
)
from aes.targets._composer import (
    compose_instincts_section,
    compose_instructions,
    compose_lifecycle_to_markdown,
    compose_openclaw_json,
    compose_rules_section,
    merge_skill_to_skillmd,
    translate_permissions_to_openshell,
)


class OpenClawTarget(SyncTarget):

    @property
    def name(self) -> str:
        return "openclaw"

    def plan(self, ctx: AgentContext, force: bool) -> SyncPlan:
        plan = SyncPlan(target_name=self.name)
        manifest = ctx.manifest

        # --- Sync-time enforcement ---
        identity = manifest.get("identity")
        model = manifest.get("model")

        if not identity:
            raise click.ClickException(
                "OpenClaw requires an `identity` section in agent.yaml.\n"
                "  Run `aes init --domain assistant` to scaffold one, "
                "or add it manually."
            )
        if not model:
            raise click.ClickException(
                "OpenClaw requires a `model` section in agent.yaml.\n"
                "  Add at minimum: model.provider and model.model"
            )

        channels = manifest.get("channels", {})
        if not channels:
            plan.warnings.append(
                "No `channels` configured — agent won't be reachable "
                "on any messaging platform."
            )

        # --- 1. openclaw.json ---
        oc_config = compose_openclaw_json(
            manifest, ctx.permissions, ctx.skill_metadata,
        )
        oc_config[AES_SENTINEL_JSON_KEY] = True
        oc_json = json.dumps(oc_config, indent=2) + "\n"

        plan.files.append(GeneratedFile(
            relative_path=".openclaw/openclaw.json",
            content=oc_json,
            description="OpenClaw main configuration",
            action=self._check_conflict(
                ctx.project_root, ".openclaw/openclaw.json", force,
            ),
        ))

        # --- 2. Workspace Markdown files ---
        workspace = _primary_workspace(manifest)

        # SOUL.md — persona + common rules
        persona = identity.get("persona", "")
        soul_content = persona
        # Append common rules to SOUL.md (behavioral conventions)
        if ctx.rules_files:
            common_rules = {
                k: v for k, v in ctx.rules_files.items()
                if k.startswith("common/")
            }
            if common_rules:
                rules_md = compose_rules_section(common_rules)
                if rules_md:
                    soul_content = (soul_content + "\n\n" + rules_md).strip()
        if soul_content:
            plan.files.append(_md_file(
                ctx, force, f".openclaw/{workspace}/SOUL.md",
                soul_content, "Agent persona (SOUL.md)",
            ))

        # IDENTITY.md — name + emoji
        id_name = identity.get("name", "")
        id_emoji = identity.get("emoji", "")
        if id_name or id_emoji:
            id_content = ""
            if id_emoji:
                id_content += f"# {id_emoji} {id_name}\n"
            else:
                id_content += f"# {id_name}\n"
            plan.files.append(_md_file(
                ctx, force, f".openclaw/{workspace}/IDENTITY.md",
                id_content, "Agent identity",
            ))

        # USER.md — user profile
        user_profile = identity.get("user_profile", "")
        if user_profile:
            plan.files.append(_md_file(
                ctx, force, f".openclaw/{workspace}/USER.md",
                user_profile, "User profile",
            ))

        # AGENTS.md — composed instructions
        header = (
            AES_SENTINEL_MD
            + "\n# "
            + manifest.get("name", "Agent")
            + " — Operating Instructions"
        )
        agents_md = compose_instructions(
            project_name=manifest.get("name", "Agent"),
            instructions=ctx.instructions,
            orchestrator=ctx.orchestrator,
            skill_runbooks=ctx.skill_runbooks,
            memory_project=ctx.memory_project,
            header=header,
        )
        # Lifecycle hooks as instructions
        if ctx.lifecycle:
            lc_md = compose_lifecycle_to_markdown(ctx.lifecycle)
            if lc_md:
                agents_md += "\n" + lc_md

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
                agents_md += "\n" + instincts_md

        plan.files.append(GeneratedFile(
            relative_path=f".openclaw/{workspace}/AGENTS.md",
            content=agents_md,
            description="Agent operating instructions",
            action=self._check_conflict(
                ctx.project_root,
                f".openclaw/{workspace}/AGENTS.md",
                force,
            ),
        ))

        # MEMORY.md — scaffold
        memory_content = ctx.memory_project or ""
        plan.files.append(_md_file(
            ctx, force, f".openclaw/{workspace}/MEMORY.md",
            memory_content or "# Agent Memory\n\n"
            "Persistent memory written by the agent across sessions.\n",
            "Persistent memory",
        ))

        # HEARTBEAT.md — heartbeat checklist (merge lifecycle heartbeat if present)
        heartbeat = manifest.get("heartbeat", {})
        hb_checklist = heartbeat.get("checklist", "")
        hb_interval = heartbeat.get("interval_minutes", 30)

        # Lifecycle heartbeat supersedes agent.yaml heartbeat when present
        lc_hb = (ctx.lifecycle or {}).get("hooks", {}).get("heartbeat")
        if lc_hb:
            hb_interval = lc_hb.get("interval_minutes", hb_interval)

        hb_content = f"# Heartbeat (every {hb_interval} minutes)\n\n"
        if hb_checklist:
            hb_content += hb_checklist.strip() + "\n"

        # Add lifecycle heartbeat actions
        if lc_hb:
            for action in lc_hb.get("actions", []):
                name = action.get("name", "unnamed")
                desc = action.get("description", "").strip()
                hb_content += f"\n- **{name}**: {desc}\n"

        if not hb_checklist and not lc_hb:
            hb_content += "<!-- Add tasks to run on each heartbeat cycle -->\n"
        plan.files.append(_md_file(
            ctx, force, f".openclaw/{workspace}/HEARTBEAT.md",
            hb_content, "Heartbeat scheduler checklist",
        ))

        # TOOLS.md — scaffold
        plan.files.append(_md_file(
            ctx, force, f".openclaw/{workspace}/TOOLS.md",
            "# Tool Notes\n\n"
            "User-maintained notes about tool usage patterns.\n",
            "Tool usage notes",
        ))

        # --- 3. Skills → SKILL.md ---
        for skill_id, runbook in ctx.skill_runbooks.items():
            meta = ctx.skill_metadata.get(skill_id, {})
            safe_id = skill_id.replace("/", "-").replace("\\", "-")
            skill_md = merge_skill_to_skillmd(skill_id, meta, runbook)

            rel_path = f".openclaw/{workspace}/skills/{safe_id}/SKILL.md"
            plan.files.append(GeneratedFile(
                relative_path=rel_path,
                content=AES_SENTINEL_MD + "\n" + skill_md,
                description=f"Skill: {meta.get('name', skill_id)}",
                action=self._check_conflict(
                    ctx.project_root, rel_path, force,
                ),
            ))

        # --- 4. Additional agent workspaces ---
        agents_list = manifest.get("agents", [])
        for agent in agents_list:
            agent_id = agent.get("id", "")
            agent_workspace = agent.get("workspace", f"workspace-{agent_id}")
            if agent_workspace == workspace:
                continue  # skip the primary workspace

            # Scaffold SOUL.md and IDENTITY.md for sub-agents
            plan.files.append(_md_file(
                ctx, force,
                f".openclaw/{agent_workspace}/SOUL.md",
                identity.get("persona", ""),
                f"Sub-agent {agent_id} persona",
            ))
            plan.files.append(_md_file(
                ctx, force,
                f".openclaw/{agent_workspace}/IDENTITY.md",
                f"# {identity.get('name', agent_id)} ({agent_id})\n",
                f"Sub-agent {agent_id} identity",
            ))

        # --- 5. OpenShell policy.yaml ---
        sandbox = manifest.get("sandbox", {})
        if sandbox.get("runtime") == "openshell" and ctx.permissions:
            policy = translate_permissions_to_openshell(ctx.permissions)
            policy_yaml = yaml.dump(
                policy, default_flow_style=False, sort_keys=False,
            )
            policy_content = (
                "# OpenShell sandbox policy\n"
                f"# {AES_SENTINEL_MD}\n"
                "#\n"
                "# Static policies (filesystem, process) are locked at "
                "sandbox creation.\n"
                "# Dynamic policies (network, inference) are "
                "hot-reloadable via `openshell policy set`.\n\n"
                + policy_yaml
            )
            plan.files.append(GeneratedFile(
                relative_path=".openclaw/policy.yaml",
                content=policy_content,
                description="OpenShell sandbox policy",
                action=self._check_conflict(
                    ctx.project_root, ".openclaw/policy.yaml", force,
                ),
            ))

        # --- 6. .env.example ---
        env_vars = _collect_env_vars(manifest)
        if env_vars:
            env_lines = [
                "# Required environment variables for OpenClaw",
                f"# {AES_SENTINEL_MD}",
                "",
            ]
            for var, desc in sorted(env_vars.items()):
                env_lines.append(f"# {desc}")
                env_lines.append(f"{var}=")
                env_lines.append("")
            plan.files.append(GeneratedFile(
                relative_path=".openclaw/.env.example",
                content="\n".join(env_lines),
                description="Required environment variables",
                action=self._check_conflict(
                    ctx.project_root, ".openclaw/.env.example", force,
                ),
            ))

        # --- 7. DEPLOY.md ---
        deploy_content = _build_deploy_guide(manifest, env_vars)
        plan.files.append(GeneratedFile(
            relative_path=".openclaw/DEPLOY.md",
            content=AES_SENTINEL_MD + "\n" + deploy_content,
            description="Deployment guide",
            action=self._check_conflict(
                ctx.project_root, ".openclaw/DEPLOY.md", force,
            ),
        ))

        return plan


def _primary_workspace(manifest: dict) -> str:
    """Determine the primary workspace directory name."""
    agents = manifest.get("agents", [])
    if agents:
        first = agents[0]
        return first.get("workspace", "workspace")
    return "workspace"


def _md_file(
    ctx: AgentContext,
    force: bool,
    rel_path: str,
    content: str,
    description: str,
) -> GeneratedFile:
    """Create a Markdown GeneratedFile with sentinel."""
    full_content = AES_SENTINEL_MD + "\n" + content.strip() + "\n"
    # Determine action via conflict detection on the target path
    full_path = ctx.project_root / rel_path
    if not full_path.exists():
        action = "create"
    elif AES_SENTINEL_MD in full_path.read_text():
        action = "update"
    elif force:
        action = "update"
    else:
        action = "conflict"
    return GeneratedFile(
        relative_path=rel_path,
        content=full_content,
        description=description,
        action=action,
    )


def _collect_env_vars(manifest: dict) -> Dict[str, str]:
    """Collect all environment variable references from the manifest."""
    env_vars: Dict[str, str] = {}

    model = manifest.get("model", {})
    if model.get("api_key_env"):
        env_vars[model["api_key_env"]] = "LLM API key"

    for fb in model.get("fallback", []):
        if fb.get("api_key_env"):
            env_vars[fb["api_key_env"]] = "Fallback LLM API key"

    channels = manifest.get("channels", {})
    for platform, cfg in channels.items():
        if isinstance(cfg, dict) and cfg.get("bot_token_env"):
            env_vars[cfg["bot_token_env"]] = f"{platform.title()} bot token"

    mcp_servers = manifest.get("mcp_servers", {})
    for name, srv in mcp_servers.items():
        if isinstance(srv, dict):
            for k, v in srv.get("env", {}).items():
                if isinstance(v, str) and v.startswith("${"):
                    var = v.strip("${}")
                    env_vars[var] = f"MCP server '{name}' — {k}"
                elif k.endswith("_ENV"):
                    env_vars[v] = f"MCP server '{name}'"

    return env_vars


def _build_deploy_guide(
    manifest: dict,
    env_vars: Dict[str, str],
) -> str:
    """Build a deployment guide tailored to the project's configuration."""
    name = manifest.get("name", "my-assistant")
    channels = manifest.get("channels", {})
    sandbox = manifest.get("sandbox", {})
    heartbeat = manifest.get("heartbeat", {})
    hb_interval = heartbeat.get("interval_minutes", 30)

    enabled_channels = [
        p for p, cfg in channels.items()
        if isinstance(cfg, dict) and cfg.get("enabled", True)
    ]
    channel_str = ", ".join(enabled_channels) if enabled_channels else "none configured"
    uses_openshell = sandbox.get("runtime") == "openshell"

    # Build env var block for the guide
    env_block = ""
    if env_vars:
        env_block = "\n".join(f"export {var}=\"...\"" for var in sorted(env_vars))

    sections: List[str] = []

    sections.append(f"# Deploying {name}\n")
    sections.append(
        f"This agent connects to **{channel_str}** "
        f"and runs a heartbeat every **{hb_interval} minutes**.\n"
    )

    # Prerequisites
    sections.append("## Prerequisites\n")
    sections.append("- Node.js >= 22")
    sections.append("- OpenClaw installed (`npm install -g @openclaw/cli`)")
    if uses_openshell:
        sections.append("- Docker (for OpenShell sandbox)")
        sections.append("- NemoClaw plugin (`openclaw plugin install nemoclaw`)")
    sections.append("")

    # Environment variables
    sections.append("## Environment Variables\n")
    sections.append(
        "Copy `.env.example` to `.env` and fill in the values, "
        "or export them directly:\n"
    )
    sections.append("```bash")
    if env_block:
        sections.append(env_block)
    else:
        sections.append("# No environment variables required")
    sections.append("```\n")

    # --- Option 1: Local / Mac Mini ---
    sections.append("## Option 1: Local Machine (laptop, Mac Mini, desktop)\n")
    sections.append(
        "Best for personal use. A Mac Mini or any always-on machine "
        "works great as a dedicated home server.\n"
    )
    sections.append("```bash")
    sections.append("# Copy the config to OpenClaw's default location")
    sections.append(f"cp -r .openclaw/ ~/.openclaw/")
    sections.append("")
    sections.append("# Or point OpenClaw at this directory")
    sections.append(f"export OPENCLAW_DIR=\"$(pwd)/.openclaw\"")
    sections.append("")
    sections.append("# Start the agent")
    sections.append("openclaw gateway")
    sections.append("```\n")
    sections.append(
        "To keep it running after you close the terminal:\n"
    )
    sections.append("```bash")
    sections.append("# macOS: use launchd (survives reboots)")
    sections.append(f"# Create ~/Library/LaunchAgents/com.openclaw.{name}.plist")
    sections.append(f"# Or simply: nohup openclaw gateway &")
    sections.append("")
    sections.append("# Linux: use systemd (see Option 2)")
    sections.append("```\n")

    # --- Option 2: VPS ---
    sections.append("## Option 2: VPS / Remote Server\n")
    sections.append(
        "Best for reliability. Any $5-10/month VPS "
        "(Hetzner, DigitalOcean, Linode) works.\n"
    )
    sections.append("```bash")
    sections.append("# 1. Copy files to the server")
    sections.append(f"scp -r .openclaw/ user@your-server:~/.openclaw/")
    sections.append("")
    sections.append("# 2. SSH in and install OpenClaw")
    sections.append("ssh user@your-server")
    sections.append("npm install -g @openclaw/cli")
    sections.append("")
    sections.append("# 3. Set environment variables")
    if env_block:
        for var in sorted(env_vars):
            sections.append(f"export {var}=\"...\"")
    sections.append("")
    sections.append("# 4. Create a systemd service for auto-start")
    sections.append(f"sudo tee /etc/systemd/system/openclaw-{name}.service << 'EOF'")
    sections.append("[Unit]")
    sections.append(f"Description=OpenClaw {name}")
    sections.append("After=network.target")
    sections.append("")
    sections.append("[Service]")
    sections.append("Type=simple")
    sections.append("User=your-user")
    sections.append("Environment=OPENCLAW_DIR=/home/your-user/.openclaw")
    if env_vars:
        for var in sorted(env_vars):
            sections.append(f"Environment={var}=YOUR_VALUE_HERE")
    sections.append("ExecStart=/usr/bin/env openclaw gateway")
    sections.append("Restart=always")
    sections.append("RestartSec=10")
    sections.append("")
    sections.append("[Install]")
    sections.append("WantedBy=multi-user.target")
    sections.append("EOF")
    sections.append("")
    sections.append(f"sudo systemctl enable --now openclaw-{name}")
    sections.append("```\n")

    # --- Option 3: Docker ---
    sections.append("## Option 3: Docker\n")
    sections.append("```bash")
    sections.append("# Run with the official OpenClaw image")
    env_flag_lines = [
        f"  -e {var}=\"${var}\"" for var in sorted(env_vars)
    ] if env_vars else []
    sections.append("docker run -d \\")
    sections.append(f"  --name {name} \\")
    sections.append("  -v $(pwd)/.openclaw:/root/.openclaw \\")
    for flag in env_flag_lines:
        sections.append(flag + " \\")
    sections.append("  --restart unless-stopped \\")
    sections.append("  openclaw/openclaw:latest gateway")
    sections.append("```\n")

    # --- Option 4: NemoClaw (if openshell) ---
    if uses_openshell:
        sections.append("## Option 4: NemoClaw (Sandboxed)\n")
        sections.append(
            "Runs inside an OpenShell sandbox with network policies, "
            "filesystem isolation, and managed inference routing.\n"
        )
        sections.append("```bash")
        sections.append("# First-time setup")
        sections.append("nemoclaw setup")
        sections.append("")
        sections.append("# Launch with default inference profile")
        sections.append("openclaw nemoclaw launch")
        sections.append("")
        sections.append("# Or with local NVIDIA NIM")
        sections.append("openclaw nemoclaw launch --profile nim-local")
        sections.append("")
        sections.append("# Monitor from the TUI")
        sections.append("nemoclaw term")
        sections.append("```\n")

    # --- Verify ---
    sections.append("## Verify It's Running\n")
    sections.append("```bash")
    sections.append("# Check gateway status")
    sections.append("openclaw status")
    sections.append("")
    sections.append("# View logs")
    sections.append("openclaw logs -f")
    if enabled_channels:
        sections.append("")
        sections.append(
            f"# Send a message on {enabled_channels[0]} — "
            "the agent should respond"
        )
    sections.append("```\n")

    return "\n".join(sections)
