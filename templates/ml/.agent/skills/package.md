# Skill: Package Model

## Purpose

Export the best model in its native serialization format and bundle it into a deployment-ready zip.

## When to Run

- Dataset has a best experiment that passes quality gates
- After evaluate skill confirms passes_quality_gates=true

## How It Works

1. Load best experiment and its trained model
2. Export in native format (CatBoost .cbm, XGBoost .json, LightGBM .txt, sklearn .joblib)
3. Generate model card with metrics and metadata
4. Create zip bundle: model file + model card + config
5. Verify bundle integrity
6. Advance to `packaged`

## Decision Tree

```
Load best experiment:
  ├── Model file exists? → Export in native format
  │   ├── CatBoost? → .cbm format
  │   ├── XGBoost? → .json format
  │   ├── LightGBM? → .txt format
  │   └── sklearn? → .joblib format
  ├── Model file missing? → Abort, re-train needed
  └── Bundle created? → Verify checksum, advance status
```

## Error Handling

- **Model file missing**: Abort, dataset stays at trained
- **Serialization error**: Log error, try alternative format
- **Zip creation failure**: Retry once, then abort
