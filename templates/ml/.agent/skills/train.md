# Skill: Train Models

## Purpose

Run Optuna hyperparameter optimization and train all candidate models for a dataset.

## When to Run

- Dataset is at `classified` status
- Resource limits met (CPU <70%, memory <75%)

## How It Works

For each selected model:
1. Preprocess data (framework-aware)
2. Run Optuna HPO (TPESampler, MedianPruner)
3. Train final model on best params
4. Evaluate on held-out test set
5. Save model in native format
6. Log to MLflow and SQLite

## Decision Tree

```
For each model_key in selected_models:
  ├── Preprocess fails? → Mark experiment failed, continue
  ├── Optuna finds no good trial? → Mark failed, continue
  ├── Training crashes? → Mark failed with error_message, continue
  └── Success? → Save model, log metrics, mark completed

After all models:
  ├── At least 1 completed? → Status: "trained"
  └── All failed? → Status: "rejected"
```

## Error Handling

- Each model trains independently (per-item-isolation)
- One model failing doesn't affect others
- Error messages stored in experiment.error_message
