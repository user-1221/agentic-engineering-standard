# Skill: Examine Dataset

## Purpose

Download a dataset, compute quality score, detect feature types, and decide if it's worth training on.

## When to Run

- Dataset is at `discovered` status
- After discover skill completes

## How It Works

1. Download data from source (OpenML API or Kaggle)
2. Compute quality score (weighted): missing 30%, dupes 15%, constants 15%, imbalance 20%, features 10%, cardinality 10%
3. Check hard rejections: >50% missing, <3 features, <10 minority samples
4. Detect feature types: numeric, categorical, datetime, text
5. Save as parquet
6. Advance to `examined`

## Decision Tree

```
Download dataset
├── Download fails? → Reject: "download_failed"
├── >50% missing values? → Reject: "too_many_missing"
├── <3 features? → Reject: "too_few_features"
├── <10 minority samples? → Reject: "insufficient_minority"
├── Quality score < 0.30? → Still advance (classify will gate)
└── Passes? → Status: "examined"
```

## Code Location

- Primary: `pipeline/examine.py`
- Quality: `_compute_quality_score()` returns `(score, diagnostics)` tuple
- Rejection: `_check_hard_rejections()` returns `str | None`
