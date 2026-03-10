# 03 — Skills: Portable, Shareable Skill Definitions

Skills are the atomic unit of agentic work. Each skill is a self-contained operation that an agent can execute — like a function, but for AI agents. Skills are composable, versionable, and shareable.

## Structure

Every skill has two files:

1. **Manifest** (`{name}.skill.yaml`) — structured metadata for tooling
2. **Runbook** (`{name}.md`) — reasoning context for the agent

Plus an optional **Orchestrator** (`ORCHESTRATOR.md`) that sequences all skills.

## Location

`.agent/skills/` — all skill files live here.

```
.agent/skills/
  ORCHESTRATOR.md          # Master sequencing skill
  discover.skill.yaml      # Manifest: inputs, outputs, triggers
  discover.md              # Runbook: how to think and execute
  train.skill.yaml
  train.md
  deploy.skill.yaml
  deploy.md
```

## Skill Manifest Format

```yaml
# .agent/skills/discover.skill.yaml
aes_skill: "1.0"

# ── Identity ──────────────────────────────────────────────
id: "discover"
name: "Discover Datasets"
version: "1.0.0"
description: "Find new public datasets from OpenML and Kaggle APIs. Use when the pipeline needs fresh data or no datasets are in discovered status. Queries multiple sources, deduplicates, and filters by quality criteria."

# ── Activation & Triggers ────────────────────────────────
activation: "explicit"              # explicit | auto | hybrid
negative_triggers:
  - "Do NOT use for manual CSV imports or local file ingestion"

# ── Position in Pipeline ──────────────────────────────────
stage: 1                        # execution order
phase: "ingestion"              # logical grouping

# ── Inputs ────────────────────────────────────────────────
inputs:
  required:
    - name: "db_connection"
      type: "sqlite3.Connection"
      description: "Active database connection"
  optional:
    - name: "max_datasets"
      type: "int"
      default: 50
      description: "Maximum datasets to discover per run"
  environment:
    - "OPENML_APIKEY"
    - "KAGGLE_USERNAME"

# ── Outputs ───────────────────────────────────────────────
outputs:
  - name: "new_dataset_ids"
    type: "list[int]"
    description: "IDs of newly discovered datasets"
  state_change:
    entity: "dataset"
    from_status: null             # creates new records
    to_status: "discovered"

# ── Prerequisites ─────────────────────────────────────────
prerequisites:
  - "Database initialized"
  - "API keys configured"

# ── Triggers ──────────────────────────────────────────────
triggers:
  - type: "manual"
    command: "python scripts/run.py --stage discover"
  - type: "schedule"
    cron: "0 3 * * *"
  - type: "condition"
    when: "no items in 'discovered' status"

# ── Error Handling ────────────────────────────────────────
error_handling:
  strategy: "per-item-isolation"
  retries: 1
  on_network_error: "log_and_continue"
  on_rate_limit: "sleep_and_retry"
  on_invalid_data: "skip_with_log"

# ── Per-Skill Permissions ────────────────────────────────
allowed_tools:
  shell: true
  files:
    read: true
    write: ["pipeline/**", "data/**"]
  network: true                      # needs API access

# ── Code References ───────────────────────────────────────
code:
  primary: "pipeline/discover.py"
  functions:
    - "discover(conn) -> list[int]"
    - "dataset_exists(conn, source, source_id) -> bool"

# ── Dependencies ──────────────────────────────────────────
depends_on: []                    # no prerequisites
blocks: ["examine"]               # must complete before examine

# ── Tags ──────────────────────────────────────────────────
tags: ["data-ingestion", "api", "openml", "kaggle"]
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `aes_skill` | string | Spec version (`"1.0"`) |
| `id` | string | Unique identifier (kebab-case) |
| `name` | string | Human-readable name |
| `version` | string | Semver |
| `description` | string | One-line summary (max 1024 chars, see guidelines below) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `negative_triggers` | string[] | Phrases describing when **not** to use this skill |
| `activation` | enum | `"explicit"` (default), `"auto"`, or `"hybrid"` — see Activation Modes |
| `allowed_tools` | object | Per-skill tool permissions (shell, files, network, mcp_servers) |
| `stage` | int | Execution order in pipeline |
| `phase` | string | Logical grouping |
| `inputs` | object | Required/optional inputs + env vars |
| `outputs` | array | What gets created or changed |
| `prerequisites` | array | Conditions that must be true |
| `triggers` | array | How the skill is invoked |
| `error_handling` | object | Error recovery strategies |
| `code` | object | Source file references |
| `depends_on` | array | Skills that must run first |
| `blocks` | array | Skills that wait on this one |
| `tags` | array | For discovery and search |

## Description Guidelines

The description is the primary signal agents use to decide whether to activate a skill. Follow this formula:

**`[What it does] + [When to use it] + [Key capabilities]`**

Good example:
```
"Find new public datasets from OpenML and Kaggle APIs. Use when the pipeline needs fresh data or no datasets are in discovered status. Queries multiple sources, deduplicates, and filters by quality criteria."
```

Bad examples:
```
"TODO: describe what this skill does"      # Placeholder — agent cannot match
"Discover datasets"                         # Too vague — when? from where?
```

Rules:
- Keep under **1024 characters** — agents truncate longer descriptions
- Be specific about **trigger conditions** ("Use when...", "Run after...")
- Include key **capabilities** the agent can match against
- Use `negative_triggers` for exclusions instead of cluttering the description

### Negative Triggers

Use `negative_triggers` to explicitly state when a skill should **not** be activated:

```yaml
negative_triggers:
  - "Do NOT use for manual data entry or CSV imports"
  - "Do NOT use when API keys are not configured"
```

These are appended to skill index entries during sync so agents can avoid false matches.

## Activation Modes

The `activation` field controls how an agent discovers and loads a skill:

| Mode | Behavior |
|------|----------|
| `explicit` (default) | Available only as a slash command. Agent must be explicitly told to use it. |
| `auto` | Description and summary are inlined into the main instructions document. Agent activates based on context matching. |
| `hybrid` | Both: inlined for auto-matching AND available as a slash command. |

```yaml
activation: "auto"    # Orchestrators, system-level skills
activation: "explicit" # Pipeline stages, specific operations (default)
activation: "hybrid"   # Skills useful both ways
```

Guidelines:
- **Orchestrators** and system-level skills → `auto`
- **Pipeline stages** and specific operations → `explicit`
- **Utility skills** that could be useful either way → `hybrid`

> **Note:** Activation mode affects Claude Code target output. Other targets (Cursor, Copilot, Windsurf) inline all skills regardless of mode.

## Per-Skill Allowed Tools

The `allowed_tools` field provides fine-grained, tool-agnostic permission hints per skill:

```yaml
allowed_tools:
  shell: true
  files:
    read: true
    write: ["src/**", "config/**"]
  network: true
  mcp_servers: ["fetch", "database"]
```

| Key | Type | Description |
|-----|------|-------------|
| `shell` | bool | Whether shell/terminal access is needed |
| `files.read` | bool or string[] | File read access (true = all, list = patterns) |
| `files.write` | bool or string[] | File write access (true = all, list = patterns) |
| `network` | bool | Whether network/HTTP access is needed |
| `mcp_servers` | string[] | MCP servers this skill requires |

These are **advisory** — sync targets render them as guidance in generated files. They do not enforce access control.

## Skill Runbook Format

The runbook is what the agent actually reads when executing a skill. It's Markdown optimized for agent reasoning.

```markdown
# Skill: Discover Datasets

## Purpose

Find new public datasets from OpenML and Kaggle that meet quality
and licensing criteria.

## When to Run

- No datasets in `discovered` status
- User requests new data sources
- Scheduled daily at 3am

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| db_connection | Connection | Yes | Active DB connection |
| max_datasets | int | No (50) | Cap on new discoveries |

## Outputs

- New dataset records at status `discovered`
- Attribution records with license and citation info

## How It Works

1. Query OpenML API for datasets matching size/license filters
2. Query Kaggle API for datasets in target domains
3. Deduplicate against existing records via `dataset_exists()`
4. Insert new records via `insert_dataset()`
5. Record attribution via `insert_attribution()`

## Decision Tree

```
For each candidate dataset:
  ├── Already exists? → Skip
  ├── License not in whitelist? → Skip
  ├── Rows < 100 or > 500,000? → Skip
  ├── Features < 3? → Skip
  └── Passes all checks? → Insert as "discovered"
```

## Error Handling

- **API timeout**: Log warning, retry once, then skip source
- **Rate limit**: Sleep for `API_RATE_LIMIT_SLEEP` seconds, retry
- **Invalid response**: Log debug info, skip dataset
- **DB error**: Rollback transaction, re-raise (fatal)

## Code Location

- Primary: `pipeline/discover.py`
- Config: `config/settings.py` (API keys, rate limits, size bounds)
- DB: `db/registry.py` (`insert_dataset`, `dataset_exists`)
```

## Orchestrator Format

The `ORCHESTRATOR.md` is a special skill that sequences all other skills. It's the agent's playbook for running the full system.

```markdown
# {System Name} — Orchestrator

## Pipeline

```
discover → examine → classify → train → evaluate → package → publish
```

## Status Flow

```
discovered → examined → classified → training → trained → packaged → published
                                                            ↗
                                                     rejected (any stage)
```

## Decision Tree

```
for each pending_stage:
  1. Check resource limits (CPU <70%, memory <75%)
  2. Get items at current status
  3. For each item:
     a. Run stage skill
     b. On success: advance status
     c. On failure: log error, mark rejected if unrecoverable
  4. Report: N processed, N failed, N skipped
```

## When to Stop

- All items at terminal status (published or rejected)
- Resource limits exceeded
- User requests stop
- No items to process at any stage
```

## Scaling Guidelines

- **20–50 skills** is the recommended range for a single project. Beyond 50, agents struggle with context window limits and skill selection accuracy.
- If you exceed 50 skills, consider splitting into sub-projects or using orchestrators to group related skills.
- `aes validate` warns when a project exceeds 50 skills.
- Prefer fewer, well-described skills over many narrow ones.

## Sharing Skills

Skills are the atomic unit of sharing. A publishable skill is a directory:

```
my-skill/
  skill.yaml          # Manifest
  runbook.md          # Runbook
  README.md           # Human documentation
  tests/              # Tests (optional)
  examples/           # Usage examples (optional)
```

See [09-sharing.md](09-sharing.md) for publishing and dependency management.
