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
description: "Find new public datasets from OpenML and Kaggle"

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
| `description` | string | One-line summary |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
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
