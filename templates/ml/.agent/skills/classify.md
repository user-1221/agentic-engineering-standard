# Skill: Classify Problem

## Purpose

Detect the problem type (binary, multiclass, regression, time-series, anomaly, clustering) and select candidate models from the model registry.

## When to Run

- Dataset is at `examined` status
- After examine skill completes with quality_score >= 0.30

## How It Works

1. Load dataset profile from examine stage
2. Analyze target column: cardinality, distribution, dtype
3. Detect problem type using heuristics
4. Query model_registry for compatible models
5. Filter models by dataset size and feature types
6. Save selected models and advance to `classified`

## Decision Tree

```
Analyze target column:
  ├── Numeric + high cardinality? → regression
  ├── Categorical + 2 classes? → binary_classification
  ├── Categorical + 3+ classes? → multiclass_classification
  ├── Datetime target? → time_series
  ├── No target column? → clustering or anomaly_detection
  └── Ambiguous? → Default to multiclass_classification

For each compatible model:
  ├── Supports problem type? → Include
  └── Not compatible? → Skip
```

## Error Handling

- **Ambiguous target**: Default to multiclass, log warning
- **No compatible models**: Reject dataset with reason
