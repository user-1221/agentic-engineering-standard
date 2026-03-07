# Skill: Evaluate Models

## Purpose

Compare all trained models, detect overfitting, check quality gates, and select the best experiment.

## When to Run

- Dataset is at `trained` status
- At least one experiment completed successfully

## How It Works

1. Load all completed experiments for the dataset
2. Rank by primary metric (accuracy, RMSE, etc.)
3. Check overfitting: train-val gap > 0.15 is a warning
4. Check quality gates: minimum metric thresholds
5. Check baseline: best model must beat random/majority
6. Select best experiment and advance to `evaluated`

## Decision Tree

```
For each completed experiment:
  ├── Train-val gap > 0.15? → Flag overfitting warning
  ├── Below quality gate? → Mark as not passing
  ├── Worse than baseline? → Mark as not passing
  └── Passes all checks? → Candidate for best

After ranking:
  ├── At least 1 passes? → Select best, status: ready for packaging
  └── None pass? → Consider reframe (back to classify)
```

## Error Handling

- **No experiments**: Cannot evaluate, keep at trained status
- **All overfitting**: Log warning, still select best if above quality gate
