# 07 — Memory: Persistent Agent Learning

Memory allows agents to learn across sessions. Instead of starting fresh each time, the agent builds up project knowledge, records decisions, and avoids repeating mistakes.

## Origin

Extracted from `.claude/projects/.../memory/MEMORY.md` — the ML Model Factory's persistent memory that tracks architecture decisions, deployment notes, and iteration history across conversations.

## Location

`.agent/memory/` — all memory files live here.

```
.agent/memory/
  project.md            # Core project knowledge (checked into git)
  learnings.yaml        # Structured lessons (checked into git)
  sessions/             # Per-session snapshots (gitignored)
    2026-02-26.md
```

## Git Strategy

| File | Git Status | Reason |
|------|-----------|--------|
| `project.md` | Tracked | Shared knowledge benefits all developers |
| `learnings.yaml` | Tracked | Structured lessons are reusable |
| `sessions/` | Gitignored | Session-specific, may contain sensitive data |

## Project Memory: `project.md`

The core knowledge file. Updated as the project evolves.

### Required Sections

```markdown
# {Project Name} — Agent Memory

## Project Overview
{What the system does. Updated as architecture changes.}

## Architecture
{Key technical decisions and their rationale.}

## Status
{Current state: what's built, in progress, planned.}

## Key Patterns
{Patterns learned from working in this codebase.}

## Environment Notes
{Deployment details, runtime quirks, infrastructure.}
```

### Guidelines

- Keep under 200 lines (agents have context limits)
- Organize semantically by topic, not chronologically
- Update or remove entries that become outdated
- Don't duplicate what's in `instructions.md`

## Structured Learnings: `learnings.yaml`

Machine-parseable lessons that influence future decisions.

```yaml
# .agent/memory/learnings.yaml
learnings:
  - id: "ordinal-targets"
    date: "2026-02-26"
    context: "Wine quality dataset, 6 integer classes"
    observation: "Auto-classified as multiclass, all models F1 ~0.33"
    lesson: >
      Ordinal integer targets with imbalanced classes should be
      reframed as regression.
    applies_when:
      - "target is ordinal integer"
      - "multiclass models all fail quality gates"
    action: "Reframe as regression, retrain"

  - id: "catboost-high-cardinality"
    date: "2026-02-25"
    context: "Dataset with 50+ unique categorical values"
    observation: "One-hot encoding caused memory explosion"
    lesson: >
      Prioritize CatBoost for high-cardinality categoricals —
      it handles them natively without encoding.
    applies_when:
      - "any categorical feature has >50 unique values"
    action: "Ensure CatBoost is in selected models"
```

### Learning Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier (kebab-case) |
| `date` | Yes | When the learning was recorded |
| `context` | Yes | What was happening when this was learned |
| `observation` | Yes | What was observed |
| `lesson` | Yes | The generalized takeaway |
| `applies_when` | No | Conditions where this learning is relevant |
| `action` | No | What to do when this learning applies |

### How Agents Use Learnings

Before executing a skill, the agent should scan `learnings.yaml` for entries whose `applies_when` conditions match the current context. This prevents repeating known mistakes.

## Session Memory: `sessions/`

Per-session notes. Created automatically during work, gitignored by default.

```markdown
# Session: 2026-02-26

## What I Did
- Trained models for dataset 42 (wine quality)
- Initial multiclass run: all models below F1 gate
- Reframed to regression: CatBoost R2=0.511 (passed)
- Packaged and published

## Decisions Made
- Chose regression over multiclass for ordinal target
- Widened CatBoost learning_rate range to 0.005-0.5

## Open Questions
- Should the classifier auto-detect ordinal targets?
```

## Operations Memory: `operations.md`

Unified chronological log across all workflow commands. Entries are interleaved — every command appends to the same Activity Log, tagged with its name. Each command tracks a **Read Cursor** so it knows what's new since its last session.

### Structure

```markdown
# Project — Operations Memory

> Unified chronological log across all commands.
> Read the entire log when starting any command.
> Update your Read Cursor after reading.

## Workers

| Command | Specialty | Read Cursor |
|---------|-----------|-------------|
| /build | Constructing the codebase | 8 |
| /train | ML training pipelines | 14 |

## Activity Log

1. [/build] 2026-03-07: Project Structure — created pipeline/, trainers/, config/
2. [/build] 2026-03-07: Database — SQLite schema for datasets, models, runs
3. [/build] 2026-03-07: Pipeline Stages — all 7 modules implemented
4. [/build] 2026-03-07: Tests — 148 passing
5. [/train] 2026-03-08: Discover — found 3 datasets from OpenML
6. [/train] 2026-03-08: Train — CatBoost R2=0.511 for dataset 42
7. [/build] 2026-03-08: Hotfix — fixed import in evaluate.py
8. [/train] 2026-03-08: Evaluate — 3 models passed quality gates

## Issues & Decisions

- [/build] Chose SQLite over Postgres for simplicity
- [/train] Ordinal targets should be reframed as regression
```

### How the Read Cursor Works

Each command stores the last entry number it has read. When starting a new session:

1. Read the full Activity Log
2. Entries after your Read Cursor are **new** — other workers did these since you last ran
3. Use this context to inform your work
4. After finishing, update your Read Cursor to the last entry number

### Guidelines

- The agent reads the **entire file** before starting any command
- Entries are numbered sequentially and tagged with `[/command]`
- Each command appends to the shared Activity Log — no separate sections
- Cross-cutting issues go in Issues & Decisions, tagged with command
- Keep the log practical — summarize, don't dump raw output

### Git Strategy

| File | Git Status | Reason |
|------|-----------|--------|
| `operations.md` | Tracked | Shared operational state benefits all developers |

## What to Remember

Save:
- Stable patterns confirmed across multiple interactions
- Key architectural decisions and their rationale
- Solutions to recurring problems
- User preferences for workflow and communication

Don't save:
- Temporary state (current task, in-progress work)
- Unverified conclusions from a single observation
- Information that duplicates `instructions.md`
- Session-specific details (file paths, IDs) in project memory

## The `/memory` Command

A cross-domain command available in all AES projects. It reviews the current conversation and persists memory-worthy items to the appropriate files. Unlike workflow commands (`/train`, `/build`), it has no Worker Identity or operations.md coordination — it operates on memory files directly.

### Activation

- **Explicit**: Run `/memory` manually at any point
- **Auto-trigger**: Agent self-triggers at the end of significant work sessions

### Target Files

| File | When to Write |
|------|--------------|
| `project.md` | Architecture decisions, status changes, key patterns, environment notes |
| `learnings.yaml` | Hard-won lessons confirmed across observations or requiring significant effort to discover |
| `sessions/` | Session snapshots for substantial work sessions |

### Phases

1. **Review Context** — scan conversation for memory-worthy items
2. **Check Existing Memory** — read current files to avoid duplicates; update, replace, or skip as appropriate
3. **Save to Project Memory** — append to `project.md` sections, keeping under 200 lines
4. **Save Structured Learnings** — append to `learnings.yaml` for confirmed, hard-won insights
5. **Session Snapshot** — optionally create `sessions/YYYY-MM-DD.md`
6. **Report** — summarize what was saved, updated, or skipped

## Memory Lifecycle

1. **During work**: Agent records observations in session memory
2. **After work**: Agent promotes stable patterns to `project.md`
3. **After repeated confirmation**: Agent records structured learnings in `learnings.yaml`
4. **Periodically**: Agent reviews and prunes outdated entries
5. **On demand or auto-trigger**: The `/memory` command reviews conversation context and saves to appropriate memory files
