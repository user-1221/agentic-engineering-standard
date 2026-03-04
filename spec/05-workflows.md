# 05 — Workflows: State Machine Definitions

Workflows define how entities move through your system. They are explicit state machines — making the implicit status tracking in your code visible, validated, and shareable.

## Origin

Extracted from the ML Model Factory's `db/models.py` where datasets flow through statuses: `discovered → examined → classified → trained → packaged → published | rejected`. Each pipeline stage reads one status and writes the next.

## Location

`.agent/workflows/` — one YAML file per entity lifecycle.

```
.agent/workflows/
  pipeline.yaml          # Dataset lifecycle
  experiment.yaml        # Experiment lifecycle
```

## Format

```yaml
# .agent/workflows/pipeline.yaml
aes_workflow: "1.0"

id: "dataset_pipeline"
entity: "dataset"
description: "Dataset lifecycle from discovery through publication"

# ── States ────────────────────────────────────────────────
states:
  discovered:
    description: "Found and registered in database"
    initial: true

  examined:
    description: "Downloaded, profiled, quality-scored"

  classified:
    description: "Problem type detected, candidate models selected"

  training:
    description: "Model training in progress"
    active: true

  trained:
    description: "All models trained, awaiting evaluation"

  packaged:
    description: "Best model packaged as distributable artifact"

  published:
    description: "Live on API and external platforms"
    terminal: true

  rejected:
    description: "Failed quality criteria"
    terminal: true

# ── Transitions ───────────────────────────────────────────
transitions:
  - from: "discovered"
    to: "examined"
    skill: "examine"
    conditions:
      - "Data file is downloadable"
    on_failure: "rejected"

  - from: "examined"
    to: "classified"
    skill: "classify"
    conditions:
      - "quality_score >= 0.30"
    on_failure: "rejected"

  - from: "classified"
    to: "training"
    skill: "train"
    conditions:
      - "At least one model selected"
      - "Resource limits met"

  - from: "training"
    to: "trained"
    skill: "train"
    conditions:
      - "At least one experiment completed"
    on_failure: "rejected"

  - from: "trained"
    to: "packaged"
    skill: "package"
    conditions:
      - "Best experiment passes quality gates"
      - "Best experiment beats baseline"
    on_failure: "rejected"

  - from: "packaged"
    to: "published"
    skill: "publish"
    conditions:
      - "At least one platform succeeds"

  # Backward transition (reframe loop)
  - from: "trained"
    to: "classified"
    skill: "reclassify"
    conditions:
      - "All models below quality gates"
      - "Problem type reframe is viable"
    description: "Reset to try different problem type"

# ── Rejection ─────────────────────────────────────────────
rejection:
  any_state_can_reject: true
  requires_reason: true
  column: "rejection_reason"

# ── Idempotency ───────────────────────────────────────────
idempotency:
  pattern: "status-gated"
  description: >
    Each skill reads entities at its expected input status.
    Already-processed entities are skipped. Safe to re-run.

# ── Persistence ───────────────────────────────────────────
persistence:
  backend: "sqlite"
  table: "datasets"
  status_column: "status"
  updated_at: "updated_at"
```

## State Types

| Property | Meaning |
|----------|---------|
| `initial: true` | Entry point. New entities start here. |
| `active: true` | Work is in progress (not yet complete). |
| `terminal: true` | No further transitions. Entity is done. |
| (none) | Intermediate state. |

## Transitions

Each transition defines:

| Field | Required | Description |
|-------|----------|-------------|
| `from` | Yes | Source state |
| `to` | Yes | Target state |
| `skill` | No | Which skill executes this transition |
| `conditions` | No | What must be true for the transition |
| `on_failure` | No | Where to go if conditions aren't met |
| `description` | No | Why this transition exists |

## Backward Transitions

Not all workflows are strictly forward. The ML Model Factory has a "reframe loop" where a dataset goes from `trained` back to `classified` when all models fail quality gates. This is modeled as a normal transition with conditions.

## Visualization

The workflow YAML generates ASCII state diagrams:

```
discovered ──→ examined ──→ classified ──→ training ──→ trained ──→ packaged ──→ published
    │              │                                      │   │
    ↓              ↓                                      │   ↓
 rejected      rejected                                   │  rejected
                                                          │
                                                          └──→ classified (reframe)
```

The `aes inspect` command renders this from the YAML.

## Idempotency Pattern

The **status-gated** pattern is the recommended default:

1. Each skill reads entities at a specific status
2. Processes each entity independently
3. Updates status on success
4. Marks rejected with reason on failure
5. Re-running skips already-processed entities

This pattern requires no external coordination — the status column IS the coordination mechanism.

## Multiple Workflows

A project can have multiple workflows for different entities:

```yaml
# .agent/workflows/experiment.yaml
aes_workflow: "1.0"

id: "experiment_lifecycle"
entity: "experiment"

states:
  pending:
    initial: true
  running:
    active: true
  completed:
    terminal: true
  failed:
    terminal: true

transitions:
  - from: "pending"
    to: "running"
    skill: "train"
  - from: "running"
    to: "completed"
    conditions: ["Training finished without error"]
  - from: "running"
    to: "failed"
    conditions: ["Exception during training"]
```

## When to Define a Workflow

Use workflows when:
- Entities move through discrete stages
- You need idempotent re-runs
- Multiple agents or processes touch the same entities
- You want to visualize the system's state machine

Skip workflows for:
- Simple request-response patterns (no state)
- Linear scripts that always run start-to-finish
