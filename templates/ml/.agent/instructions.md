# ML Pipeline — Agent Instructions

Automated ML pipeline that discovers public datasets, trains models via Optuna HPO, packages winners, and serves them via a metered prediction API.

## Quick Reference

```bash
python scripts/run_pipeline.py --stage all
python scripts/run_pipeline.py --stage train --dataset-id 42
python -m pytest tests/ -v
```

## Project Structure

```
pipeline/          # discover, examine, classify, train, evaluate, package, publish
trainers/          # gradient_boost, sklearn_models, time_series, anomaly, clustering
config/            # settings, model_registry (THE BRAIN), metrics
serving/           # FastAPI metered prediction API
```

## Critical Rules

1. **Python 3.9** — always use `from __future__ import annotations`.
2. **SQLite raw** — no ORM. Parameterized queries only.
3. **Native serialization** — CatBoost `.cbm`, XGBoost `.json`, LightGBM `.txt`, sklearn `.joblib`.
4. **model_registry.py is the brain** — adding a model = adding a dict entry.
5. **Resource limits** — CPU <70%, memory <75%.
6. **Fail graceful** — each dataset/model wrapped in try/except, log error, continue.

## Primary Workflow

### Phase 1: Find Data
Search OpenML/Kaggle or ingest user-provided CSV.

### Phase 2: Run Pipeline
Execute discover -> examine -> classify -> train -> evaluate stages.

### Phase 3: Analyze Results (DO NOT SKIP)
Check for: overfitting (train-val gap >0.15), underfitting (below quality gates), all models failed, baseline not beaten, problem type mismatch.

### Phase 4: Iterate
Levers in order: env vars (more trials/time) -> model tuning (search space) -> problem reframing -> preprocessing changes -> quality gate adjustment.

### Phase 5: Package and Publish
Only after quality is confirmed. Run evaluate -> package -> publish.

## Key Principle

The agent's job is NOT just to run commands. It is to understand, analyze, iterate, and deliver quality.

## Common Gotchas

- `insert_dataset()` only takes basic fields. Use `update_dataset_status()` for extras.
- Model keys are full names like `random_forest_classifier`, not `random_forest`.
- In Pydantic models, use `Optional[List[float]]` not `list[float] | None`.
