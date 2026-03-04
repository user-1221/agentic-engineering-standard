# Command: /train

End-to-end model training — from finding data to publishing a model.

## Phase 1: Gather Requirements

Ask the user:
- What do they want to predict?
- Do they have data, or should we search?
- Any constraints (time, compute, accuracy)?

## Phase 2: Find or Ingest Data

**If searching**: Query OpenML/Kaggle.
**If user provides data**: Upload CSV, register in DB.

## Phase 3: Run Pipeline

```bash
scripts/job.sh start {ID} --stage examine
scripts/job.sh start {ID} --stage classify
scripts/job.sh start {ID}
```

## Phase 4: Analyze Results (DO NOT SKIP)

1. **Overfitting**: train-val gap > 0.15 → increase regularization
2. **Underfitting**: all below gates → more trials/time
3. **All failed**: check error_message → fix preprocessing
4. **Baseline not beaten** → dataset may lack signal
5. **Problem type mismatch**: ordinal as multiclass → reframe to regression

## Phase 5: Iterate

Quick: OPTUNA_N_TRIALS=100, OPTUNA_TIMEOUT=600
Moderate: widen/narrow search space in registry
Significant: change preprocessing, lower quality gates

## Phase 6: Package and Publish

```bash
scripts/job.sh start {ID} --stage evaluate
scripts/job.sh start {ID} --stage package
scripts/job.sh start {ID} --stage publish
```

## Phase 7: Report

Model key, test metrics, API endpoint, HuggingFace URL, caveats.
