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

## Memory Lifecycle

1. **During work**: Agent records observations in session memory
2. **After work**: Agent promotes stable patterns to `project.md`
3. **After repeated confirmation**: Agent records structured learnings in `learnings.yaml`
4. **Periodically**: Agent reviews and prunes outdated entries
