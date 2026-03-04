# ML Model Factory — Orchestrator

## Pipeline

```
discover → examine → classify → train → evaluate → package → publish
```

## Status Flow

```
discovered → examined → classified → training → trained → packaged → published
    │            │                                 │
    ↓            ↓                                 ↓
 rejected     rejected                          rejected
                                                   │
                                                   └──→ classified (reframe loop)
```

## Decision Tree

```
for each stage in [discover, examine, classify, train, evaluate, package, publish]:
  1. Check resource limits (CPU <70%, memory <75%)
  2. Get datasets at current status (or single dataset if --dataset-id)
  3. For each dataset:
     a. Run stage function
     b. On success: advance status to next stage
     c. On failure: log error, mark rejected if unrecoverable
  4. Report: N processed, N failed, N skipped

Special: after train stage, run ANALYSIS before evaluate:
  - Check overfitting (train-val gap >0.15)
  - Check underfitting (all below quality gates)
  - Check baseline (better than random?)
  - If all fail: consider reframe (trained → classified)
```

## When to Stop

- All datasets at terminal status (published or rejected)
- Resource limits exceeded
- User requests stop
- No datasets to process
