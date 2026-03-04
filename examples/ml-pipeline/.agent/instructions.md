# ML Model Factory — Agent Instructions

Automated ML pipeline that discovers public datasets, trains models via Optuna HPO, packages winners, and serves them via a metered prediction API. Runs on a Hetzner VPS alongside a crypto bot — never exceed resource limits.

## Quick Reference

```bash
# VPS training (async)
scripts/job.sh start 42
scripts/job.sh status mf-42-20260225-143000
scripts/job.sh results 42

# Local dev
python scripts/run_pipeline.py --stage all
python scripts/run_pipeline.py --stage train --dataset-id 42
python -m pytest tests/ -v
```

## Project Structure

```
config/
  settings.py          # paths, env vars, resource limits
  model_registry.py    # 27 models across 7 problem types (THE BRAIN)
  metrics.py           # per-problem-type metrics and quality gates
pipeline/
  discover.py          # find OpenML/Kaggle datasets
  examine.py           # profile + quality score
  classify.py          # problem type detection + model selection
  train.py             # Optuna HPO + model training
  evaluate.py          # ranking + quality gates
  package.py           # zip packaging
  publish.py           # API + HuggingFace publishing
trainers/
  gradient_boost.py    # CatBoost, XGBoost, LightGBM
  sklearn_models.py    # RF, LogReg, SVM, KNN
  time_series.py       # Prophet, ARIMA
  anomaly.py           # IsolationForest, LOF
  clustering.py        # KMeans, HDBSCAN
  nlp_lightweight.py   # TF-IDF + sklearn
serving/
  app.py               # FastAPI metered prediction API
  auth.py              # API key auth + rate limiting
```

## Critical Rules

1. **Python 3.9** — always use `from __future__ import annotations`.
2. **SQLite raw** — no ORM. Parameterized queries only.
3. **Native serialization** — CatBoost `.cbm`, XGBoost `.json`, LightGBM `.txt`, sklearn `.joblib`.
4. **model_registry.py is the brain** — adding a model = adding a dict entry.
5. **Resource limits** — CPU <70%, memory <75%. Crypto bot must not be disturbed.
6. **Fail graceful** — each dataset/model wrapped in try/except, log error, continue.

## Primary Workflow: "Create a Model That Predicts X"

### Phase 1: Find Data
Search OpenML/Kaggle or ingest user-provided CSV.

### Phase 2: Run Pipeline
```bash
scripts/job.sh start {ID} --stage examine
scripts/job.sh start {ID} --stage classify
scripts/job.sh start {ID}
```

### Phase 3: Analyze Results (DO NOT SKIP)
Check for: overfitting (train-val gap >0.15), underfitting (below quality gates), all models failed, baseline not beaten, problem type mismatch.

### Phase 4: Iterate
Levers in order: env vars (more trials/time) → model tuning (search space) → problem reframing → preprocessing changes → quality gate adjustment.

### Phase 5: Package and Publish
Only after quality is confirmed. Run evaluate → package → publish.

## Key Principle

The agent's job is NOT just to run commands. It is to understand, analyze, iterate, and deliver quality.

## Common Gotchas

- `insert_dataset()` only takes basic fields. Use `update_dataset_status()` for extras.
- Model keys are full names like `random_forest_classifier`, not `random_forest`.
- In Pydantic models, use `Optional[List[float]]` not `list[float] | None`.
