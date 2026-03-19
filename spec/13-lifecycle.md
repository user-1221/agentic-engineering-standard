# 13 — Lifecycle Hooks

Lifecycle hooks let agents run scripts at session boundaries, before and after tool calls, on periodic heartbeats, and on errors. They enable session continuity (restoring context from the previous session), quality gates (blocking dangerous operations), audit trails (logging every tool call), and proactive behavior (periodic task checking). Hook declarations are portable — defined once in `.agent/lifecycle.yaml` and compiled to each sync target's native format.

## Motivation

- **Session continuity**: Restore previous session context at start, persist summaries at end — agents never start cold
- **Quality gates**: Validate tool calls before execution, blocking dangerous operations in strict environments
- **Audit trails**: Log tool usage, inputs, outputs, and durations for compliance and debugging
- **Proactive behavior**: Periodic heartbeat hooks let agents check tasks and manage context without waiting for user input
- **Portable declarations**: Define hooks once, compile to Claude Code, OpenClaw, Cursor, Codex, and future targets

## Location

`.agent/lifecycle.yaml` — always at this path, always this filename.

Hook implementation scripts live in `.agent/scripts/`. Hook output (logs, audit trails) goes to `.agent/logs/`.

## Format

YAML with comments. Validated against `schemas/lifecycle.schema.json`.

```yaml
# .agent/lifecycle.yaml
apiVersion: aes/v1
kind: Lifecycle

# --- Runtime profile (controls which hooks are active) ---
profile: standard                  # minimal | standard | strict

# --- Disabled hooks (override without editing this file) ---
# Also controllable via AES_DISABLED_HOOKS env var
disabled_hooks: []

# --- Hook definitions ---
hooks:

  # SESSION LIFECYCLE

  on_session_start:
    - name: restore-context
      description: >
        Load previous session summary, active instincts,
        and persistent memory into agent context.
      profile: minimal              # Available in all profiles
      action: script
      command: node .agent/scripts/restore-context.js
      timeout_seconds: 10
      async: false                  # Block until context is loaded
      fail_strategy: warn           # warn | skip | abort
      inputs:
        - memory_dir: .agent/memory/
        - learning_dir: .agent/learning/instincts/active/
        - sessions_dir: .agent/learning/sessions/

  on_session_end:
    - name: persist-summary
      description: >
        Save a compressed summary of this session for
        the next session's restore-context hook.
      profile: minimal
      action: script
      command: node .agent/scripts/persist-summary.js
      timeout_seconds: 15
      async: true                   # Don't block session exit
      fail_strategy: warn

    - name: extract-instincts
      description: >
        Review session actions and extract candidate
        instincts for the learning system.
      profile: standard             # Not in minimal profile
      action: script
      command: node .agent/scripts/extract-instincts.js
      timeout_seconds: 30
      async: true
      fail_strategy: skip

  # TOOL LIFECYCLE

  pre_tool_use:
    - name: quality-gate
      description: >
        Validate tool calls against project rules.
        Blocks dangerous operations in strict mode.
      profile: strict               # Only in strict profile
      action: script
      command: node .agent/scripts/quality-gate.js
      filter:
        tools: [Edit, Write, Bash, Execute]
      timeout_seconds: 5
      async: false                  # Must complete before tool runs
      fail_strategy: abort          # Block the tool call on failure

    - name: doc-warning
      description: >
        Warn before modifying documentation files
        unless explicitly instructed.
      profile: standard
      action: script
      command: node .agent/scripts/doc-warning.js
      filter:
        tools: [Edit, Write]
        paths: ["*.md", "docs/**"]
      timeout_seconds: 3
      async: false
      fail_strategy: warn

  post_tool_use:
    - name: audit-log
      description: >
        Log tool name, input, output, duration,
        and result status for audit trail.
      profile: standard
      action: script
      command: node .agent/scripts/audit-log.js
      async: true
      fail_strategy: skip
      output:
        file: .agent/logs/audit.jsonl
        format: jsonl

  # PERIODIC

  heartbeat:
    interval_minutes: 30
    actions:
      - name: check-tasks
        description: Review pending tasks and act proactively
        action: checklist
        checklist_file: .agent/heartbeat.md

      - name: compact-check
        description: >
          Check accumulated context size and suggest
          compaction if above threshold.
        action: script
        command: node .agent/scripts/compact-check.js
        config:
          threshold_tokens: 100000

  # ERROR HANDLING

  on_error:
    - name: error-recovery
      description: >
        Attempt graceful recovery: save state,
        log error context, retry if transient.
      action: script
      command: node .agent/scripts/error-recovery.js
      max_retries: 3
      backoff_seconds: 5
      fail_strategy: warn
```

## Profile System

Profiles control which hooks are active at runtime. Each hook declares the minimum profile it requires. Higher profiles include all hooks from lower profiles.

| Profile | Active Hooks | Use Case |
|---------|-------------|----------|
| `minimal` | Only hooks with `profile: minimal` (session start/end) | Debugging, low-overhead sessions, quick tasks |
| `standard` | `minimal` + hooks with `profile: standard` (audit, doc-warning, instinct extraction) | Normal development work |
| `strict` | `standard` + hooks with `profile: strict` (quality gates with abort-on-fail) | Production code, regulated environments, CI/CD |

The hierarchy is cumulative: `strict` includes everything from `standard`, which includes everything from `minimal`.

Set the active profile in `lifecycle.yaml` via the `profile` field, or override at runtime with the `AES_HOOK_PROFILE` environment variable. The environment variable takes precedence when set.

## Hook Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for this hook (kebab-case, unique within its event type) |
| `description` | string | Yes | What this hook does (shown in `aes inspect`) |
| `profile` | enum | No (default: `standard`) | Minimum profile to activate: `minimal`, `standard`, `strict` |
| `action` | enum | Yes | Execution type: `script` or `checklist` |
| `command` | string | If `action: script` | Shell command to execute (prefer Node.js for cross-platform) |
| `checklist_file` | string | If `action: checklist` | Markdown file with checklist items |
| `filter.tools` | string[] | No | Only trigger for these tool types (pre/post_tool_use only) |
| `filter.paths` | string[] | No | Only trigger for files matching these globs (pre/post_tool_use only) |
| `timeout_seconds` | integer | No (default: 30) | Max execution time before the hook is killed |
| `async` | boolean | No (default: `false`) | Run in background without blocking the agent |
| `fail_strategy` | enum | No (default: `warn`) | On failure: `warn` (log and continue), `skip` (silent), `abort` (block the action) |
| `inputs` | object | No | Data paths passed to the script as environment variables or arguments |
| `output.file` | string | No | Where the hook writes its output |
| `output.format` | string | No | Output format: `jsonl`, `json`, or `md` |
| `max_retries` | integer | No | For `on_error` hooks only: number of retry attempts |
| `backoff_seconds` | integer | No | For `on_error` hooks only: delay between retries |
| `config` | object | No | Arbitrary key-value pairs passed to the script |

## Event Types

### on_session_start

Fired when an agent session begins. Use for restoring context, loading memory, and injecting active instincts.

- Hooks run sequentially in declaration order
- Typically `async: false` — the agent should wait for context before proceeding
- `fail_strategy: warn` is recommended — a failed restore should not block the session

### on_session_end

Fired when an agent session terminates (user exits, timeout, or explicit stop). Use for persisting session summaries, extracting learned patterns, and cleanup.

- Hooks may run as `async: true` since the session is ending
- The session transcript is available to scripts at this point (platform-specific access)
- `fail_strategy: warn` or `skip` is recommended — do not block session exit

### pre_tool_use

Fired before a tool call is executed. Use for quality gates, validation, and warnings.

- Supports `filter.tools` and `filter.paths` to narrow which tool calls trigger the hook
- `async: false` is required for hooks that need to block execution
- `fail_strategy: abort` blocks the tool call entirely when the hook fails
- `fail_strategy: warn` logs a warning but allows the tool call to proceed

### post_tool_use

Fired after a tool call completes. Use for audit logging, metrics collection, and post-execution checks.

- Supports `filter.tools` and `filter.paths` to narrow which tool calls trigger the hook
- Typically `async: true` — logging should not slow down the agent
- Receives tool name, input, output, duration, and result status

### heartbeat

Fired on a periodic interval during long-running sessions. Use for proactive task checking, context compaction, and autonomous behaviors.

- `interval_minutes` sets the period between heartbeat fires
- Each action in the `actions` list runs on every heartbeat tick
- `action: checklist` reads a Markdown file and presents items for the agent to review
- `action: script` runs a script that can inspect state and suggest actions

### on_error

Fired when the agent encounters an unrecoverable error. Use for graceful recovery, state preservation, and retry logic.

- `max_retries` and `backoff_seconds` control retry behavior (only valid on this event type)
- Backoff is linear: first retry after `backoff_seconds`, second after `2 * backoff_seconds`, etc.
- After `max_retries` exhausted, the `fail_strategy` determines final behavior

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AES_HOOK_PROFILE` | Override the active profile at runtime (takes precedence over `lifecycle.yaml`) | `AES_HOOK_PROFILE=minimal` |
| `AES_DISABLED_HOOKS` | Comma-separated list of hook names to disable at runtime | `AES_DISABLED_HOOKS=audit-log,compact-check` |

Both variables allow runtime control without editing `lifecycle.yaml`. This is useful for debugging (disable noisy hooks), CI/CD (enforce strict profile), or quick tasks (use minimal profile).

The `disabled_hooks` field in `lifecycle.yaml` and the `AES_DISABLED_HOOKS` environment variable are merged — a hook disabled by either mechanism is skipped. The environment variable does not replace the YAML list; it adds to it.

## Compilation Targets

`aes sync` compiles `lifecycle.yaml` into platform-specific hook configurations:

| Sync Target | Output | Fidelity |
|-------------|--------|----------|
| Claude Code | `.claude/hooks.json` | Full — native hook system with event types, timeouts, async, and tool filters |
| OpenClaw | Gateway events + `workspace/HEARTBEAT.md` | Full — session hooks map to gateway events, heartbeat to built-in scheduler, tool hooks to middleware |
| Cursor | `.cursor/hooks/` + `.cursor/rules/` | Partial — tool hooks map to automation rules, session hooks compiled as rule entries |
| Codex | Behavioral instructions in `AGENTS.md` | Lossy — no native hook system; hooks are written as behavioral instructions (model compliance, no runtime enforcement) |
| Copilot | Skip | No hook support — lifecycle.yaml is not compiled for this target |
| Windsurf | Skip | No hook support — lifecycle.yaml is not compiled for this target |

### Claude Code

Claude Code has native lifecycle hook support. `aes sync -t claude` generates `.claude/hooks.json`:

```json
{
  "hooks": [
    {
      "type": "command",
      "event": "SessionStart",
      "command": "node .agent/scripts/restore-context.js",
      "timeout": 10
    },
    {
      "type": "command",
      "event": "Stop",
      "command": "node .agent/scripts/persist-summary.js",
      "async": true,
      "timeout": 15
    },
    {
      "type": "command",
      "event": "PreToolUse",
      "command": "node .agent/scripts/quality-gate.js",
      "timeout": 5,
      "toolNames": ["Edit", "Write", "Bash", "Execute"]
    },
    {
      "type": "command",
      "event": "PostToolUse",
      "command": "node .agent/scripts/audit-log.js",
      "async": true
    }
  ]
}
```

Event mapping: `on_session_start` maps to `SessionStart`, `on_session_end` maps to `Stop` (not `SessionEnd` — the transcript payload is only available in the Stop phase), `pre_tool_use` maps to `PreToolUse`, `post_tool_use` maps to `PostToolUse`. Heartbeat and on_error hooks are compiled as instructions in `CLAUDE.md` since Claude Code has no native periodic or error event.

### OpenClaw

OpenClaw has a gateway event system that maps cleanly to lifecycle hooks:

| AES Hook Type | OpenClaw Output | How It Works |
|---------------|-----------------|--------------|
| `on_session_start` | Gateway startup event handler | Registered in `openclaw.json` as gateway plugin |
| `on_session_end` | Gateway shutdown event handler | Runs on SIGTERM/SIGINT |
| `heartbeat` | `workspace/HEARTBEAT.md` | OpenClaw's built-in heartbeat scheduler reads this file |
| `pre_tool_use` / `post_tool_use` | Gateway middleware | Intercepts tool calls in the agent runtime loop |
| `on_error` | Gateway error handler | Registered as error middleware |

When `lifecycle.yaml` defines a heartbeat, it supersedes any heartbeat configuration in `agent.yaml` for the OpenClaw target (see Relationship to agent.yaml heartbeat below).

### Cursor

Cursor supports limited hook-like behavior through automation rules. Only `pre_tool_use` and `post_tool_use` map to Cursor's automation system. Session hooks (`on_session_start`, `on_session_end`) are compiled as `.cursor/rules/` entries that instruct the agent to run scripts at the appropriate moments. Heartbeat and error hooks are best-effort behavioral instructions.

### Codex

Codex has no native hook system. All hooks are compiled as behavioral instruction sections embedded in `AGENTS.md`, telling the agent to execute scripts at lifecycle boundaries. This is a lossy compilation — enforcement depends on model compliance rather than runtime enforcement. Example output:

```markdown
## Lifecycle Hooks

### On Session Start
Run `node .agent/scripts/restore-context.js` before beginning work.

### Before Editing Files
Run `node .agent/scripts/quality-gate.js` before modifying code files.
```

### Copilot

Copilot has no hook support. `lifecycle.yaml` is not compiled for this target. Hooks are silently skipped during `aes sync -t copilot`.

### Windsurf

Windsurf has no hook support. `lifecycle.yaml` is not compiled for this target. Hooks are silently skipped during `aes sync -t windsurf`.

## Directory Structure

```
.agent/
  lifecycle.yaml               # Hook declarations (this spec)
  scripts/                     # Hook implementation scripts
    restore-context.js
    persist-summary.js
    extract-instincts.js
    quality-gate.js
    doc-warning.js
    audit-log.js
    compact-check.js
    error-recovery.js
  heartbeat.md                 # Heartbeat checklist (referenced by checklist hooks)
  logs/                        # Hook output directory
    audit.jsonl                # Audit trail (generated by hooks)
```

### .agent/scripts/

Hook scripts are the implementation behind `action: script` hooks. They receive context as environment variables and arguments, execute their logic, and write output to stdout or a designated file.

Scripts can be written in any language. Node.js is recommended for cross-platform compatibility.

### .agent/logs/

The `logs/` directory is for hook-generated output. It should be listed in `.agentignore` (or `.gitignore`) to avoid committing runtime artifacts. The `audit.jsonl` file is append-only — each line is a JSON object representing one tool call.

## Validation Rules

`lifecycle.yaml` is validated against `schemas/lifecycle.schema.json`. The following rules are enforced:

- `apiVersion` must be `aes/v1`
- `kind` must be `Lifecycle`
- `profile` must be one of: `minimal`, `standard`, `strict`
- Each hook `name` must be unique within its event type
- `action` must be one of: `script`, `checklist`
- `action: script` requires `command`; `action: checklist` requires `checklist_file`
- `fail_strategy` must be one of: `warn`, `skip`, `abort`
- `filter.tools` and `filter.paths` are only valid on `pre_tool_use` and `post_tool_use` hooks
- `max_retries` and `backoff_seconds` are only valid on `on_error` hooks
- `timeout_seconds` must be a positive integer
- `heartbeat.interval_minutes` must be a positive integer

`lifecycle.yaml` is optional — projects without it still validate. When present, `aes validate` checks all the rules above and warns if referenced scripts (in `command` fields) or checklist files (in `checklist_file` fields) do not exist.

## Relationship to agent.yaml heartbeat

The existing `agent.yaml` schema includes an optional `heartbeat` section used by the assistant domain and the OpenClaw target:

```yaml
# agent.yaml (existing)
heartbeat:
  interval_minutes: 30
  checklist: |
    - Check for unread messages across channels
    - Review calendar for upcoming meetings
```

The `lifecycle.yaml` heartbeat is a superset of this — it supports multiple named actions, both script and checklist action types, and per-action configuration.

**Precedence rule**: When both `agent.yaml` heartbeat and `lifecycle.yaml` heartbeat are present, `lifecycle.yaml` takes precedence. The `agent.yaml` heartbeat is ignored for sync targets that support lifecycle hooks.

- If only `agent.yaml` has a heartbeat: sync targets use it (backward compatible, no change)
- If only `lifecycle.yaml` has a heartbeat: sync targets use it
- If both are present: `lifecycle.yaml` wins; `aes validate` emits an informational warning noting the override

The `agent.yaml` heartbeat remains in the schema for backward compatibility and for projects that do not need the full lifecycle hook system. Projects adopting `lifecycle.yaml` should migrate their heartbeat configuration there and remove it from `agent.yaml` to avoid the warning.
