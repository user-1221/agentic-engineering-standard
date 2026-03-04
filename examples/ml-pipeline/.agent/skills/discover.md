# Skill: Discover Datasets

## Purpose

Find new public datasets from OpenML and Kaggle that meet quality and licensing criteria.

## When to Run

- No datasets in `discovered` status
- User requests new data sources
- Scheduled daily

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| db_connection | Connection | Yes | Active DB connection |
| max_datasets | int | No (50) | Cap on discoveries |

## Outputs

- New dataset records at status `discovered`
- Attribution records with license and citation

## How It Works

1. Query OpenML API for datasets matching size/license filters
2. Query Kaggle API for datasets in target domains
3. Deduplicate against existing records via `dataset_exists()`
4. Insert new records via `insert_dataset()`
5. Record attribution via `insert_attribution()`

## Decision Tree

```
For each candidate dataset:
  ├── Already exists? → Skip
  ├── License not in whitelist? → Skip
  ├── Rows < 100 or > 500,000? → Skip
  ├── Features < 3? → Skip
  └── Passes all checks? → Insert as "discovered"
```

## Error Handling

- **API timeout**: Retry once, then skip source
- **Rate limit**: Sleep `API_RATE_LIMIT_SLEEP` seconds, retry
- **Invalid response**: Log debug, skip dataset

## Code Location

- Primary: `pipeline/discover.py`
- Config: `config/settings.py`
- DB: `db/registry.py`
