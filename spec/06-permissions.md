# 06 — Permissions: Agent Capability Boundaries

Permissions define what an agent can do, what it must never do, and what requires human confirmation. The permission model is tool-agnostic — each agent tool translates it into its native format.

## Origin

Extracted from `.claude/settings.local.json` which uses glob patterns to allowlist safe operations (status checks, log reads) while implicitly blocking dangerous ones (container deletion, service restarts).

## Location

`.agent/permissions.yaml`

## Format

```yaml
# .agent/permissions.yaml
aes_permissions: "1.0"

# ── ALLOW: Agent can do these without asking ──────────────
allow:
  shell:
    read:
      - "git status"
      - "git log *"
      - "git diff *"
      - "ls *"
      - "scripts/job.sh status *"
      - "scripts/job.sh logs *"
      - "scripts/job.sh list"
      - "scripts/job.sh results *"
    execute:
      - "python scripts/run.py *"
      - "python -m pytest *"
      - "docker compose logs *"
    remote:
      - "ssh user@host *"

  files:
    read: "**/*"
    write:
      - "config/**/*.py"
      - "pipeline/**/*.py"
      - "trainers/**/*.py"
      - ".agent/memory/**"
    create:
      - "data/**"
      - "models/**"
      - "tests/**"

# ── DENY: Agent must NEVER do these ──────────────────────
deny:
  shell:
    - "rm -rf *"
    - "docker rm *"
    - "systemctl *"
    - "kill *"
    - "chmod 777 *"
    - "DROP TABLE *"
    - "DELETE FROM * WHERE 1=1"
  files:
    write:
      - ".env"
      - ".env.*"
      - "*.pem"
      - "*.key"
      - "*.sqlite3"
      - ".git/**"
    delete:
      - ".env"
      - "*.sqlite3"

# ── CONFIRM: Agent must ask before doing these ────────────
confirm:
  shell:
    - "scripts/job.sh stop *"
    - "docker compose down *"
    - "docker compose restart *"
    - "scp *"
    - "git push *"
    - "git reset *"
  files:
    delete: "**/*"
  actions:
    - "publish_model"
    - "create_api_key"
    - "modify_quality_gates"
    - "delete_experiments"

# ── Resource Limits ───────────────────────────────────────
resource_limits:
  max_cpu_percent: 70
  max_memory_percent: 75
  check_before:
    - "train"
    - "evaluate"
  on_exceeded: "warn_and_skip"

# ── Tool-Specific Overrides ──────────────────────────────
# Optional. Only needed when generic format is insufficient.
overrides:
  claude:
    permissions:
      allow:
        - "Bash(ssh:*)"
        - "Bash(*job.sh status*)"
        - "Bash(*job.sh logs*)"
  cursor:
    allowed_commands: ["git", "python", "docker"]
```

## Permission Categories

### Allow

Actions the agent can take without asking. Subdivided by type:

- **shell.read** — read-only commands (status, logs, diffs)
- **shell.execute** — commands that do work (run scripts, tests)
- **shell.remote** — remote access commands
- **files.read** — file read patterns (glob syntax)
- **files.write** — file modification patterns
- **files.create** — file creation patterns

### Deny

Actions the agent must NEVER take, regardless of context. These are hard blocks:

- **shell** — destructive commands, service management
- **files.write** — secrets, databases, git internals
- **files.delete** — critical files

### Confirm

Actions that require human approval before execution:

- **shell** — stopping services, pushing code, file transfers
- **files.delete** — any file deletion
- **actions** — domain-specific operations (publishing, key creation)

## Glob Syntax

Permission patterns use glob syntax (same as `.gitignore`):

| Pattern | Matches |
|---------|---------|
| `*` | Any string within a path segment |
| `**` | Any number of path segments |
| `*.py` | All Python files |
| `config/**/*.py` | Python files anywhere under config/ |

## Resource Limits

Resource limits are checked before specific skills run:

```yaml
resource_limits:
  max_cpu_percent: 70
  max_memory_percent: 75
  check_before: ["train", "evaluate"]
  on_exceeded: "warn_and_skip"     # or "wait_and_retry", "abort"
```

Options for `on_exceeded`:
- `warn_and_skip` — log warning, skip the skill, continue pipeline
- `wait_and_retry` — wait 60s, check again, retry up to 3 times
- `abort` — stop the entire pipeline

## Network Access

Controls which URLs and endpoints the agent can reach.

```yaml
network:
  allow:
    - "https://api.anthropic.com/*"
    - "https://www.openml.org/*"
  deny:
    - "*.internal.corp/*"
  confirm:
    - "https://*.amazonaws.com/*"
```

Uses the same `allow/deny/confirm` pattern as shell and file permissions. Patterns use glob syntax.

## Process Restrictions

Controls which processes the agent can spawn.

```yaml
process:
  allow: ["python", "node", "git"]
  deny: ["curl", "wget"]
```

This is a coarser control than `shell` permissions. Where `shell` controls full command strings, `process` controls which executables can be invoked at all.

## Inference Routing

Constraints on how the agent uses AI models.

```yaml
inference:
  routing:
    - task: "code-generation"
      models: ["claude-sonnet-4-20250514"]
    - task: "summarization"
      models: ["claude-haiku-4-5-20251001"]
  max_tokens_per_request: 4096
  max_requests_per_minute: 60
```

- **routing**: Maps task types to allowed models. If a task type is not listed, any model may be used.
- **max_tokens_per_request**: Upper bound on tokens per inference call.
- **max_requests_per_minute**: Rate limit for inference calls.

## Data Classification

Policies for how the agent handles data.

```yaml
data:
  classification: "internal"       # public | internal | confidential | restricted
  retention_days: 90
  pii_handling: "prohibit"         # redact | mask | prohibit | allow
```

- **classification**: Data sensitivity level. Agents should not send `confidential` or `restricted` data to external APIs without explicit approval.
- **retention_days**: How long agent-generated data should be retained.
- **pii_handling**: How personally identifiable information should be handled.

## Overrides

The `overrides` section is for tool-specific permission formats that can't be expressed generically. Each tool reads its own section and ignores others.

This is the escape hatch — use it sparingly. The generic `allow/deny/confirm` sections should cover 90% of cases.

## Precedence

1. **Deny** always wins (if something is in both allow and deny, deny takes effect)
2. **Confirm** overrides allow (if something is in both, confirmation is required)
3. **Allow** is the default for listed patterns
4. **Everything else** requires confirmation (implicit default)

## Security Considerations

- Never put secrets in permissions.yaml (it's checked into git)
- The deny list should include destructive operations for your environment
- Resource limits protect shared infrastructure (like a VPS running multiple services)
- Tool-specific overrides should be reviewed per-tool for security implications
