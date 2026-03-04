# 02 — Instructions: `instructions.md`

The instructions file is the master playbook for the agent. It teaches the agent how to **think**, not just what to execute. This is the most important file in any agentic system.

## Location

`.agent/instructions.md` — referenced from `agent.yaml` under `agent.instructions`.

## Philosophy

A good instructions file transforms an agent from a command executor into a decision-maker. It should answer:

- What does this system do?
- What are the absolute rules?
- How do I navigate this codebase?
- What's the primary workflow, and how do I reason through it?
- What mistakes should I avoid?

## Required Sections

### 1. Header + Summary

```markdown
# {Project Name} — Agent Instructions

{One paragraph: what the system does, its primary constraints, and the
 operating environment. This is the agent's 10-second orientation.}
```

### 2. Quick Reference

Copy-paste-ready commands for the most common operations. Group by environment.

```markdown
## Quick Reference

\```bash
# Local development
python scripts/run.py --stage all
python -m pytest tests/ -v

# Remote (VPS/Cloud)
scripts/job.sh start 42
scripts/job.sh status mf-42-20260225

# Serving
docker compose up -d api
\```
```

**Why**: Agents need executable context, not documentation to read. Quick Reference gives them the exact commands.

### 3. Project Structure

Annotated directory tree. Every file or directory gets a brief comment.

```markdown
## Project Structure

\```
config/
  settings.py          # env vars, resource limits, thresholds
  registry.py          # component definitions (THE BRAIN)
pipeline/
  discover.py          # find new data sources
  process.py           # transform and validate
  deploy.py            # push to production
\```
```

**Why**: The agent's map of the codebase. Without this, agents waste turns exploring.

### 4. Critical Rules

Numbered, inviolable constraints. Use bold keywords.

```markdown
## Critical Rules

1. **Python 3.9** — always use `from __future__ import annotations`.
2. **No ORM** — raw SQL with parameterized queries only.
3. **Resource limits** — CPU <70%, memory <75%.
4. **Fail graceful** — each item wrapped in try/except, log error, continue.
```

**Why**: These are guardrails the agent must never cross, regardless of the task.

### 5. Domain Model

The core entities, their relationships, and how data flows.

```markdown
## Domain Model

**Entities**: datasets, experiments, published_models
**Flow**: datasets are discovered → examined → classified → trained
**Key relationship**: each dataset has many experiments (one per model)
```

**Why**: Gives the agent a mental model of the problem space.

### 6. Primary Workflow

The main thing the agent does. This is NOT a list of commands — it's a reasoning framework with phases, decision points, and iteration loops.

```markdown
## Primary Workflow: "Create a Model That Predicts X"

### Phase 1: Find Data
{What to search for, where, how to evaluate options}

### Phase 2: Process
{Run the pipeline, what to watch for}

### Phase 3: Analyze Results (DO NOT SKIP)
{What metrics to check, what thresholds matter, how to detect problems}

### Phase 4: Iterate
{Ordered list of levers to pull, from least to most effort}

### Phase 5: Deliver
{Only after quality is confirmed}
```

**Critical pattern**: The workflow must include an **analysis phase** that the agent cannot skip. This is what separates an agentic system from a script.

### 7. Key Principle

The philosophical anchor — one sentence that captures the system's ethos.

```markdown
## Key Principle

The agent's job is NOT just to run commands. It is to understand,
analyze, iterate, and deliver quality.
```

### 8. Extension Points

How to add new components without modifying core code.

```markdown
## Extension Points

Adding a new model: add a dict entry to `config/registry.py` and
implement the 5-function trainer interface. The pipeline discovers
it automatically.
```

### 9. Common Gotchas

Hard-won lessons that prevent mistakes.

```markdown
## Common Gotchas

- `insert_dataset()` only takes basic fields. Use `update_dataset_status()`
  for target_column, problem_type, etc.
- Model keys are full names like `random_forest_classifier`, not `random_forest`.
```

## Optional Sections

- **Database**: Schema overview, key functions, access patterns
- **API Endpoints**: Routes, authentication, rate limiting
- **Deployment**: Environment-specific instructions
- **Testing**: How to run tests, fixture patterns, coverage expectations

## Anti-Patterns

- **Too long** (>500 lines): Split into skills. Instructions should be a map, not an encyclopedia.
- **Commands without reasoning**: "Run X, then Y" without explaining when to stop or what to check.
- **No iteration loop**: The workflow assumes everything works on the first try.
- **Missing gotchas**: The agent will make the same mistakes the author made.

## Relationship to Skills

Instructions provide the **big picture** — the agent's orientation and primary workflow. Skills provide **deep dives** — detailed runbooks for specific operations. The instructions reference skills but don't duplicate them.
