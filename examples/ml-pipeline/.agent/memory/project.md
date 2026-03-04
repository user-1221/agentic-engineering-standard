# ML Model Factory — Agent Memory

## Project Overview
Automated ML pipeline that discovers public datasets, trains models via Optuna HPO, packages winners, and serves them via a metered prediction API.

## Architecture
- Python 3.9, SQLite (raw, no ORM), native model serialization
- model_registry.py is the brain — 27 models across 7 problem types
- Metered API with tiered keys (free/basic/pro/enterprise)

## Status
All core code built. 148 tests passing. Deployed on Hetzner VPS.

## Key Patterns
- All db functions take `conn` as first arg
- Pipeline stages read one status, write the next
- Trainers implement 5-function interface
