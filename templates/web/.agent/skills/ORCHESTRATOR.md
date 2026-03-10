# Web Application — Orchestrator

## Feature Development Pipeline

```
scaffold → implement → test → review → deploy
```

## Feature Status Flow

```
planned → in_progress → testing → staging → deployed
                                     ↗
                              blocked (any stage)
```

## Decision Tree

```
FIRST: Check if pipeline is already complete (all features at terminal status).
  If complete → report status summary, ask user: re-run / new session / re-validate / exit.
  If not → proceed:

1. Understand feature requirements
2. Create migration if schema change needed
3. Implement API route with auth middleware
4. Implement UI component (server-first, client when interactive)
5. Write tests (unit + integration + e2e)
6. Deploy to staging
7. Verify on staging (manual + automated checks)
8. Deploy to production behind feature flag
9. Monitor metrics, then remove flag
```
