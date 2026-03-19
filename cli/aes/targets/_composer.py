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
    skill_path_prefix: str = "/skills",
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
                auto_lines.append(f"### {name} (`{skill_path_prefix}/{skill_id}`)\n")
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
                line = f"- **{skill_path_prefix}/{skill_id}** — {name}"
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


# ---------------------------------------------------------------------------
# OpenClaw-specific composition helpers
# ---------------------------------------------------------------------------


def merge_skill_to_skillmd(
    skill_id: str,
    metadata: Dict[str, Any],
    runbook: str,
) -> str:
    """Merge AES skill metadata + runbook into a single SKILL.md.

    Output format follows the Agent Skills standard:
    YAML frontmatter (between --- delimiters) + Markdown body.
    AES-specific fields (requires, emoji, primary_env) are nested
    under ``metadata.openclaw`` as inline JSON.
    """
    import json as _json

    name = metadata.get("name", skill_id)
    description = metadata.get("description", "")
    version = metadata.get("version", "0.1.0")
    license_id = metadata.get("license", "MIT")
    user_invocable = metadata.get("user_invocable", True)

    # Build openclaw metadata JSON (requires, primaryEnv, emoji)
    oc_meta: Dict[str, Any] = {}
    requires: Dict[str, List[str]] = {}
    if metadata.get("requires_bins"):
        requires["bins"] = metadata["requires_bins"]
    if metadata.get("requires_env"):
        requires["env"] = metadata["requires_env"]
    if requires:
        oc_meta["requires"] = requires
    if metadata.get("primary_env"):
        oc_meta["primaryEnv"] = metadata["primary_env"]
    if metadata.get("emoji"):
        oc_meta["emoji"] = metadata["emoji"]

    # Assemble YAML frontmatter
    lines: List[str] = ["---"]
    lines.append(f"name: {name}")
    lines.append(f"description: {description}")
    lines.append(f"version: {version}")
    lines.append(f"license: {license_id}")
    lines.append(f"user-invocable: {'true' if user_invocable else 'false'}")
    if oc_meta:
        lines.append("metadata:")
        lines.append(f"  {_json.dumps({'openclaw': oc_meta})}")
    lines.append("---")
    lines.append("")

    # Append runbook body
    body = runbook.strip() if runbook else ""
    if body:
        lines.append(body)

    return "\n".join(lines) + "\n"


def compose_instincts_section(
    instincts: List[Dict[str, Any]],
    fmt: str = "compact",
) -> str:
    """Render active instincts as a Markdown section.

    ``fmt`` can be "compact" (description + action only) or "full"
    (includes evidence + examples).
    """
    if not instincts:
        return ""

    lines: List[str] = ["## Learned Patterns\n"]
    lines.append("The following patterns were learned from previous sessions:\n")

    for inst in instincts:
        meta = inst.get("metadata", {})
        pattern = inst.get("pattern", {})
        confidence = inst.get("confidence", {})

        inst_id = meta.get("id", "unknown")
        score = confidence.get("score", 0)

        lines.append(f"### {inst_id} (confidence: {score:.0%})\n")
        if pattern.get("description"):
            lines.append(pattern["description"].strip())
            lines.append("")

        if pattern.get("trigger"):
            lines.append(f"**When:** {pattern['trigger'].strip()}\n")

        if pattern.get("action"):
            lines.append(f"**Action:**\n{pattern['action'].strip()}\n")

        if fmt == "full":
            evidence = pattern.get("evidence", [])
            if evidence:
                lines.append("**Evidence:**")
                for ev in evidence:
                    lines.append(f"- {ev.get('session', '?')}: {ev.get('outcome', '')}")
                lines.append("")

            examples = pattern.get("examples", [])
            if examples:
                lines.append("**Examples:**")
                for ex in examples:
                    lines.append(f"- *{ex.get('context', '')}*: {ex.get('application', '')}")
                lines.append("")

    return "\n".join(lines) + "\n"


# Profile hierarchy — a hook is active if its profile level is <= the active level
_PROFILE_LEVELS = {"minimal": 0, "standard": 1, "strict": 2}


def compile_lifecycle_to_hooks_json(
    lifecycle: Dict[str, Any],
    profile: Optional[str] = None,
) -> Dict[str, Any]:
    """Compile AES lifecycle.yaml into Claude Code hooks.json format.

    Filters hooks by active profile and maps AES event types to
    Claude Code event names.
    """
    active_profile = profile or lifecycle.get("profile", "standard")
    active_level = _PROFILE_LEVELS.get(active_profile, 1)
    disabled = set(lifecycle.get("disabled_hooks", []))

    event_map = {
        "on_session_start": "SessionStart",
        "on_session_end": "Stop",
        "pre_tool_use": "PreToolUse",
        "post_tool_use": "PostToolUse",
    }

    hooks_list: List[Dict[str, Any]] = []
    hooks_section = lifecycle.get("hooks", {}) or {}

    for aes_event, claude_event in event_map.items():
        for hook in hooks_section.get(aes_event, []):
            hook_profile = hook.get("profile", "standard")
            hook_level = _PROFILE_LEVELS.get(hook_profile, 1)
            if hook_level > active_level:
                continue
            if hook.get("name") in disabled:
                continue
            if hook.get("action") != "script":
                continue

            entry: Dict[str, Any] = {
                "type": "command",
                "event": claude_event,
                "command": hook.get("command", ""),
            }
            if hook.get("timeout_seconds"):
                entry["timeout"] = hook["timeout_seconds"]
            if hook.get("async"):
                entry["async"] = True

            # Tool filter (pre/post only)
            filt = hook.get("filter", {})
            if filt.get("tools"):
                entry["toolNames"] = filt["tools"]

            hooks_list.append(entry)

    return {"hooks": hooks_list}


def compose_lifecycle_to_markdown(
    lifecycle: Dict[str, Any],
    profile: Optional[str] = None,
) -> str:
    """Compile lifecycle hooks into a Markdown instruction section.

    Used by targets that don't have native hook support (Codex, Copilot,
    Windsurf).  This is a lossy compilation — enforcement depends on
    model compliance rather than runtime enforcement.
    """
    active_profile = profile or lifecycle.get("profile", "standard")
    active_level = _PROFILE_LEVELS.get(active_profile, 1)
    disabled = set(lifecycle.get("disabled_hooks", []))

    hooks_section = lifecycle.get("hooks", {}) or {}
    lines: List[str] = ["## Lifecycle Hooks\n"]
    lines.append("Execute the following scripts at the appropriate lifecycle moments:\n")

    event_labels = {
        "on_session_start": "At Session Start",
        "on_session_end": "At Session End",
        "pre_tool_use": "Before Tool Use",
        "post_tool_use": "After Tool Use",
    }

    any_hooks = False
    for aes_event, label in event_labels.items():
        event_hooks = []
        for hook in hooks_section.get(aes_event, []):
            hook_profile = hook.get("profile", "standard")
            hook_level = _PROFILE_LEVELS.get(hook_profile, 1)
            if hook_level > active_level:
                continue
            if hook.get("name") in disabled:
                continue
            event_hooks.append(hook)

        if event_hooks:
            any_hooks = True
            lines.append(f"### {label}\n")
            for hook in event_hooks:
                name = hook.get("name", "unnamed")
                desc = hook.get("description", "").strip()
                cmd = hook.get("command", "")
                lines.append(f"- **{name}**: {desc}")
                if cmd:
                    lines.append(f"  Run: `{cmd}`")
            lines.append("")

    # Heartbeat
    heartbeat = hooks_section.get("heartbeat")
    if heartbeat:
        any_hooks = True
        interval = heartbeat.get("interval_minutes", 30)
        lines.append(f"### Periodic (every {interval} minutes)\n")
        for action in heartbeat.get("actions", []):
            name = action.get("name", "unnamed")
            desc = action.get("description", "").strip()
            lines.append(f"- **{name}**: {desc}")
        lines.append("")

    if not any_hooks:
        return ""

    return "\n".join(lines) + "\n"


def compose_rules_section(rules_files: Dict[str, str]) -> str:
    """Render rule files as a single Markdown block for inline targets.

    ``rules_files`` is keyed by ``category/filename.md`` with content
    as the value (variables already resolved).
    """
    if not rules_files:
        return ""

    lines: List[str] = ["## Conventions\n"]

    # Group by category
    categories: Dict[str, List[str]] = {}
    for key, content in rules_files.items():
        category = key.split("/")[0] if "/" in key else "common"
        categories.setdefault(category, []).append(content)

    for category, contents in categories.items():
        lines.append(f"### {category.title()} Rules\n")
        for content in contents:
            lines.append(content.strip())
            lines.append("")

    return "\n".join(lines) + "\n"


def translate_permissions_to_openshell(permissions: dict) -> dict:
    """Translate AES permissions.yaml into OpenShell's four-domain policy format.

    Returns a dict suitable for YAML serialization as ``policy.yaml``.
    Static domains: filesystem_policy, process_policy (locked at creation).
    Dynamic domains: network_policies, inference_policy (hot-reloadable).
    """
    policy: Dict[str, Any] = {}

    # --- filesystem_policy (static) ---
    fs = permissions.get("filesystem", {})
    if fs:
        policy["filesystem_policy"] = {
            "enforcement": fs.get("enforcement", "best_effort"),
            "read_only": fs.get("read_only", ["/usr", "/lib", "/etc"]),
            "read_write": fs.get("read_write", ["/sandbox", "/tmp"]),
        }
    else:
        # Derive from allow/deny files if filesystem section absent
        allow_files = permissions.get("allow", {}).get("files", {})
        deny_files = permissions.get("deny", {}).get("files", {})
        read_paths = _normalize_patterns(allow_files.get("read"))
        write_paths = _normalize_patterns(allow_files.get("write"))
        if read_paths or write_paths:
            policy["filesystem_policy"] = {
                "enforcement": "best_effort",
                "read_only": read_paths,
                "read_write": write_paths,
            }

    # --- process_policy (static) ---
    proc = permissions.get("process", {})
    policy["process_policy"] = {
        "seccomp": "RuntimeDefault",
        "allow_privilege_escalation": False,
        "run_as_non_root": True,
        "capabilities": {
            "add": [],
            "drop": ["ALL"],
        },
    }
    if proc:
        if "allow" in proc:
            policy["process_policy"]["allow"] = proc["allow"]
        if "deny" in proc:
            policy["process_policy"]["deny"] = proc["deny"]

    # --- network_policies (dynamic) ---
    net = permissions.get("network", {})
    net_policies: Dict[str, Any] = {}

    # From structured network.policies (OpenShell-native format)
    for p in permissions.get("network_policies", []):
        name = p.get("name", "unnamed")
        entry: Dict[str, Any] = {}
        if p.get("endpoints"):
            entry["endpoints"] = p["endpoints"]
        if p.get("binaries"):
            entry["binaries"] = p["binaries"]
        net_policies[name] = entry

    # From simpler network.allow URLs
    allow_urls = _normalize_patterns(net.get("allow"))
    if allow_urls and not net_policies:
        for i, url in enumerate(allow_urls):
            net_policies[f"allowed_{i}"] = {
                "endpoints": [{"host": url, "port": 443}],
            }

    if net_policies:
        policy["network_policies"] = net_policies

    # --- inference_policy (dynamic) ---
    inf = permissions.get("inference", {})
    if inf:
        inf_policy: Dict[str, Any] = {}
        if inf.get("routing"):
            inf_policy["routing"] = inf["routing"]
        if inf.get("max_tokens_per_request"):
            inf_policy["max_tokens_per_request"] = inf["max_tokens_per_request"]
        if inf.get("max_requests_per_minute"):
            inf_policy["max_requests_per_minute"] = inf["max_requests_per_minute"]
        if inf_policy:
            policy["inference_policy"] = inf_policy

    return policy


def translate_permissions_to_openclaw_tools(permissions: dict) -> dict:
    """Extract tool approval config from permissions for openclaw.json.

    Returns the ``tools.exec`` section of openclaw.json.
    """
    tools_section = permissions.get("tools", {})
    if not tools_section:
        return {}

    result: Dict[str, Any] = {}
    mode = tools_section.get("approval_mode", "ask")
    result["ask"] = mode

    assurance = tools_section.get("assurance_levels", {})
    if assurance and mode == "a2h":
        result["a2h"] = {"assurance": assurance}

    return result


def compose_openclaw_json(
    manifest: dict,
    permissions: Optional[dict],
    skill_metadata: Dict[str, Dict[str, Any]],
) -> dict:
    """Assemble a complete openclaw.json dict from AES manifest sections.

    Environment variable references use ``${VAR_NAME}`` syntax —
    raw secrets are never embedded.
    """
    config: Dict[str, Any] = {}

    # --- LLM ---
    model = manifest.get("model", {})
    if model:
        llm: Dict[str, Any] = {}
        if model.get("provider"):
            llm["provider"] = model["provider"]
        if model.get("model"):
            llm["model"] = model["model"]
        if model.get("api_key_env"):
            llm["apiKey"] = f"${{{model['api_key_env']}}}"
        if model.get("base_url"):
            llm["baseUrl"] = model["base_url"]
        if llm:
            config["llm"] = llm

    # --- Agents ---
    agents_list = manifest.get("agents", [])
    sandbox_cfg = manifest.get("sandbox", {})
    agents_section: Dict[str, Any] = {
        "defaults": {
            "sandbox": {
                "enabled": sandbox_cfg.get("enabled", False),
                "workspaceRoot": sandbox_cfg.get("workspace_root", "/sandbox"),
            },
        },
        "agents": {},
    }
    if agents_list:
        for agent in agents_list:
            agent_entry: Dict[str, Any] = {}
            if agent.get("workspace"):
                agent_entry["workspace"] = agent["workspace"]
            if agent.get("model_override"):
                agent_entry["llm"] = agent["model_override"]
            if agent.get("mcp_servers"):
                agent_entry["mcpServers"] = agent["mcp_servers"]
            agents_section["agents"][agent["id"]] = agent_entry
    else:
        # Default single agent
        agents_section["agents"]["main"] = {"workspace": "workspace"}

    config["agents"] = agents_section

    # --- Integrations (channels) ---
    channels = manifest.get("channels", {})
    if channels:
        integrations: Dict[str, Any] = {}
        for platform, cfg in channels.items():
            entry: Dict[str, Any] = {}
            if isinstance(cfg, dict):
                entry["enabled"] = cfg.get("enabled", True)
                if cfg.get("bot_token_env"):
                    entry["botToken"] = f"${{{cfg['bot_token_env']}}}"
            integrations[platform] = entry
        config["integrations"] = integrations

    # --- MCP servers ---
    mcp_servers = dict(manifest.get("mcp_servers", {}))

    # Also collect MCP servers declared inside skills
    for _skill_id, meta in skill_metadata.items():
        mcp = meta.get("mcp_server")
        if mcp and isinstance(mcp, dict):
            server_name = _skill_id.replace("_", "-")
            mcp_servers.setdefault(server_name, mcp)

    if mcp_servers:
        servers: Dict[str, Any] = {}
        for name, srv in mcp_servers.items():
            if isinstance(srv, dict):
                entry = {}
                if srv.get("command"):
                    entry["command"] = srv["command"]
                if srv.get("args"):
                    entry["args"] = srv["args"]
                if srv.get("env"):
                    # Convert _ENV references to ${} syntax
                    env: Dict[str, str] = {}
                    for k, v in srv["env"].items():
                        if isinstance(v, str) and v.startswith("${"):
                            env[k] = v
                        elif isinstance(v, str) and k.endswith("_ENV"):
                            env[k.removesuffix("_ENV")] = f"${{{v}}}"
                        else:
                            env[k] = v
                    entry["env"] = env
                if srv.get("disabled"):
                    entry["disabled"] = True
                servers[name] = entry
        config["mcp"] = {"servers": servers}

    # --- Skills config ---
    if skill_metadata:
        config["skills"] = {
            "load": {"watch": True, "watchDebounceMs": 250},
        }

    # --- Tools (from permissions) ---
    if permissions:
        tools = translate_permissions_to_openclaw_tools(permissions)
        if tools:
            config["tools"] = {"exec": tools}

    return config
