# Skill: Deploy

## Purpose

Deploy the application to staging or production.

## When to Run

- All tests pass
- Feature reviewed and approved

## How It Works

1. Build production bundle
2. Run database migrations
3. Deploy to target environment
4. Verify health check
5. Monitor error rates for 15 minutes

## Decision Tree

```
Deploy to staging
├── Health check fails? → Rollback, investigate
├── Error rate spikes? → Rollback, investigate
└── Stable for 15 min? → Promote to production (with confirmation)
```
