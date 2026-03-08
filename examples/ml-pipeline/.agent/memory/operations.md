# ML Model Factory — Operations Memory

> Unified chronological log across all commands.
> **Read the entire log** when starting any command — entries from other workers give you context.
> After reading, update your **Read Cursor** below so you know where you left off next time.
> Append new entries to the Activity Log tagged with your command.

## Workers

| Command | Specialty | Read Cursor |
|---------|-----------|-------------|
| /build | Constructing ML pipeline codebases — modules, database, stages, registry | 8 |
| /train | Executing ML training pipelines — HPO, evaluation, packaging | 14 |

## Activity Log

1. [/build] 2026-02-20: Project Structure — created pipeline/, trainers/, config/, serving/, scripts/, tests/
2. [/build] 2026-02-20: Database & Storage — SQLite schema for datasets, models, runs
3. [/build] 2026-02-20: Pipeline Stages — all 7 stage modules (discover through publish)
4. [/build] 2026-02-20: Model Registry — 27 models across 7 problem types
5. [/build] 2026-02-20: Configuration — settings.py with env-based config, quality gates
6. [/build] 2026-02-20: Scripts & CLI — run_pipeline.py with --stage and --dataset-id
7. [/build] 2026-02-20: Tests — 148 tests passing across all modules
8. [/build] 2026-02-20: Build complete — all modules verified
9. [/train] 2026-02-25: Discover — found 5 datasets from OpenML matching criteria
10. [/train] 2026-02-25: Examine — profiled all 5, rejected 1 (too small), 4 advanced
11. [/train] 2026-02-25: Classify — 2 regression, 1 multiclass, 1 binary
12. [/train] 2026-02-25: Train — ran Optuna HPO for each candidate model
13. [/train] 2026-02-26: Evaluate — 3 passed gates, wine quality failed (F1 ~0.33)
14. [/train] 2026-02-26: Reframed wine quality multiclass→regression — CatBoost R2=0.511, passed
15. [/train] 2026-02-26: Package — serialized 4 models with model cards
16. [/train] 2026-02-26: Publish — pushed all 4 to HuggingFace Hub

## Issues & Decisions

- [/build] Chose SQLite (no ORM) for single-machine deployment simplicity
- [/build] Native serialization per framework (CatBoost .cbm, XGBoost .json, LightGBM .txt)
- [/train] Wine quality: ordinal integer targets misclassified as multiclass → reframed to regression
- [/train] CatBoost consistently outperforms on high-cardinality categoricals
- [/train] Widened CatBoost learning_rate range to 0.005-0.5 for better HPO coverage
