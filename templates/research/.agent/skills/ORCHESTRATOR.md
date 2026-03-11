# Research Pipeline — Orchestrator

## Pipeline

```
ingest → parse → analyze → organize → display
```

## Status Flow

```
ingested → parsed → analyzed → organized → displayed
    │                   │
    ↓                   ↓
 rejected            rejected
```

## Decision Tree

```
FIRST: Check if pipeline is already complete (all items at terminal status).
  If complete → report status summary, ask user: re-run / new sources / export / exit.
  If not → proceed:

for each stage in [ingest, parse, analyze, organize, display]:
  1. Get items at current status (or single item if --item-id)
  2. For each item:
     a. Run stage function
     b. On success: advance status to next stage
     c. On failure: log error, mark rejected if unrecoverable
  3. Report: N processed, N failed, N skipped

Special: after analyze stage, check relevance:
  - Items with relevance_score < 0.2 → rejected
  - Items with no key findings → flag for manual review
  - Items with high similarity to existing → flag as potential duplicate
```

## When to Stop

- All items at terminal status (displayed or rejected)
- MAX_ITEMS_PER_RUN limit reached
- User requests stop
- No items to process
