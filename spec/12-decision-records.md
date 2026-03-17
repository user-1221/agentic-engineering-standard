# 12 — Agent Decision Records

Agent Decision Records (ADRs) provide structured, machine-readable documentation of significant choices an agent makes during operation. Unlike unstructured session memory, decision records are YAML files with a fixed schema — making them consumable by compliance tools, dashboards, and audit systems.

## Motivation

- **Auditability**: Trace why an agent chose one approach over another
- **Compliance**: Demonstrate that decisions were made with appropriate reasoning
- **Learning**: Future agent sessions can reference past decisions as precedent
- **Accountability**: Record whether decisions were autonomous or human-approved

## Location

`.agent/memory/decisions/` — one YAML file per decision.

```
.agent/memory/decisions/
  dr-001-regression-reframe.yaml
  dr-002-catboost-selection.yaml
  dr-003-quality-gate-override.yaml
```

### Naming Convention

Files are named `{id}-{slug}.yaml` where:
- `id` is the decision record ID (e.g., `dr-001`)
- `slug` is a human-readable kebab-case summary

## Format

YAML. Validated against `schemas/decision-record.schema.json`.

```yaml
aes_decision: "1.2"
id: "dr-001"
timestamp: "2026-03-17T14:30:00Z"
summary: "Chose regression over multiclass for ordinal target"
context: "Wine quality dataset has 6 integer classes with severe imbalance"
alternatives:
  - option: "multiclass classification"
    reason_rejected: "All models below F1=0.40 quality gate"
rationale: "Ordinal integer targets with imbalanced classes perform better as regression"
outcome: "CatBoost R2=0.511, passed quality gate"
artifacts: ["models/wine-quality-catboost-v1.pkl"]
approval:
  status: "auto"
  approved_by: null
tags: ["ml", "reframing"]
```

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `aes_decision` | Yes | AES spec version |
| `id` | Yes | Unique ID, format `dr-NNN` |
| `timestamp` | Yes | ISO 8601 datetime |
| `summary` | Yes | One-line description of the decision |
| `context` | No | Background information |
| `alternatives` | No | Options that were considered and rejected |
| `rationale` | No | Why this option was chosen |
| `outcome` | No | Result of the decision |
| `artifacts` | No | Related files or outputs |
| `approval` | No | Approval status and approver |
| `tags` | No | Categorization tags |

### Approval Status

| Value | Meaning |
|-------|---------|
| `auto` | Agent made the decision autonomously |
| `human-approved` | Human reviewed and approved |
| `human-rejected` | Human reviewed and rejected |
| `pending` | Awaiting human review |

## When to Record

Agents should create decision records for choices that:

1. **Deviate from the default path** (e.g., reframing a problem type)
2. **Involve trade-offs** (e.g., speed vs. accuracy)
3. **Reject alternatives** (e.g., tried classification, switched to regression)
4. **Have compliance implications** (e.g., choosing a model or data source)
5. **Override or modify quality gates**

Routine, low-impact choices (e.g., "used default hyperparameters") do not need records.

## Relationship to Memory

Decision records complement the existing memory system:

| File | Purpose | Format |
|------|---------|--------|
| `memory/project.md` | Evolving project knowledge | Free-form Markdown |
| `memory/learnings.yaml` | Reusable lessons | Structured YAML |
| `memory/decisions/*.yaml` | Individual decision audit trail | Structured YAML (this spec) |
| `memory/sessions/` | Per-session notes | Free-form Markdown |

Decision records are **immutable once created** — they represent a point-in-time decision. If a decision is later reversed, create a new decision record that references the original.

## Validation

```bash
aes validate          # validates all decision records in .agent/memory/decisions/
```

Decision records are validated against `schemas/decision-record.schema.json`. They are optional — projects without decision records still validate.

## Git Strategy

| File | Git Status | Reason |
|------|-----------|--------|
| `memory/decisions/*.yaml` | Tracked | Decision history benefits all developers and auditors |
