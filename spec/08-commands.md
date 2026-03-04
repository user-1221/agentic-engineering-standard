# 08 — Commands: Multi-Phase Workflow Automation

Commands are complex, multi-phase workflows that an agent executes in response to a trigger (typically a slash command like `/train`). Unlike skills which are single operations, commands orchestrate multiple skills with decision points, analysis phases, and iteration loops.

## Origin

Extracted from `.claude/commands/train.md` — a 7-phase workflow that guides the agent through dataset discovery, training, critical analysis, iteration, and publishing. It includes failure mode detection, recovery procedures, and real-world examples.

## Location

`.agent/commands/` — one Markdown file per command.

```
.agent/commands/
  train.md              # /train — end-to-end model training
  deploy.md             # /deploy — package and publish
  debug.md              # /debug — diagnose and fix issues
```

## Registration

Commands are registered in `agent.yaml`:

```yaml
commands:
  - id: "train"
    path: "commands/train.md"
    trigger: "/train"
    description: "End-to-end model training with analysis and iteration"
```

## Format

Commands follow a phase structure:

```markdown
# Command: /train

End-to-end model training — from data discovery to publication.

## Phase 1: Gather Requirements

Ask the user:
- What do they want to predict?
- Do they have data, or should we search?
- Any constraints (time, compute, accuracy)?

## Phase 2: Find or Ingest Data

**If searching**: Query OpenML/Kaggle for matching datasets.
**If user provides data**: Upload and register in database.

```bash
python scripts/run.py --stage discover --dataset-id {ID}
```

## Phase 3: Run Pipeline

```bash
python scripts/run.py --stage examine --dataset-id {ID}
python scripts/run.py --stage classify --dataset-id {ID}
python scripts/run.py --stage train --dataset-id {ID}
```

## Phase 4: Analyze Results (DO NOT SKIP)

After training, read the output and analyze:

**Check for these issues:**

1. **Overfitting**: train-val gap > 0.15
   - Fix: increase regularization, reduce complexity
2. **Underfitting**: all models below quality gates
   - Fix: more trials, wider search space, more models
3. **All models failed**: check error_message field
   - Fix: examine data, fix preprocessing
4. **Baseline not beaten**: no better than random
   - Fix: dataset may lack signal, try feature engineering
5. **Problem type mismatch**: ordinal target as multiclass
   - Fix: reframe as regression, retrain

## Phase 5: Iterate

Based on analysis, pull these levers in order:

**Quick** (no code change):
- Increase OPTUNA_N_TRIALS / OPTUNA_TIMEOUT
- Re-run training

**Moderate** (config change):
- Widen/narrow search space in registry
- Remove underperforming models

**Significant** (code change):
- Change preprocessing strategy
- Lower quality gates if problem is genuinely hard

**After changes**: rebuild, retrain, re-analyze. Repeat.

## Phase 6: Package and Publish

Only after quality is confirmed:

```bash
python scripts/run.py --stage evaluate --dataset-id {ID}
python scripts/run.py --stage package --dataset-id {ID}
python scripts/run.py --stage publish --dataset-id {ID}
```

## Phase 7: Report

Tell the user:
- Model key and framework
- Test metrics (primary + secondary)
- API endpoint for predictions
- Any caveats or limitations
```

## Key Patterns

### 1. Analysis Phase (DO NOT SKIP)

Every command that produces results must include an analysis phase. This transforms the agent from a script runner into a quality evaluator.

### 2. Failure Mode Catalog

List specific things that can go wrong, how to detect them, and how to fix them. This is the agent's troubleshooting guide.

### 3. Iteration Loop

Commands should include a "try again with adjustments" phase. The agent should not give up after one attempt.

### 4. Ordered Levers

When iterating, levers are ordered by effort — try the easiest fix first:
1. Environment variables (no code change)
2. Configuration changes (edit registry)
3. Code changes (modify logic)

### 5. Real Examples

Include concrete examples of failures and recoveries:

```markdown
### Example: Wine Quality Dataset

- Auto-classified as multiclass (6 integer classes 3-8)
- All models: F1 ~0.33 (gate: 0.60) — FAILED
- Reframed to regression: CatBoost R2=0.511 (gate: 0.50) — PASSED
- Lesson: ordinal integer targets often work better as regression
```

## Commands vs. Skills

| Aspect | Skill | Command |
|--------|-------|---------|
| Scope | Single operation | Multi-phase workflow |
| Trigger | Pipeline stage | Slash command |
| Decision points | Minimal (execute or skip) | Many (analyze, iterate, choose) |
| Iteration | None (runs once) | Built-in retry loops |
| User interaction | Minimal | Asks questions, reports results |

Commands orchestrate skills. A `/train` command might invoke the `examine`, `classify`, `train`, `evaluate`, and `package` skills, with analysis and iteration between them.
