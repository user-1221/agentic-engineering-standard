# Skill: Rollback Service

## Purpose

Revert a service to the previous known-good deployment immediately.

## When to Run

- Error rate spikes after deploy
- Health checks fail after deploy
- User requests emergency rollback

## How It Works

1. Identify previous deployment (blue instance)
2. Switch traffic back to previous
3. Verify health of reverted service
4. Log rollback event with reason
5. Keep failed deployment for debugging

## Decision Tree

```
Rollback initiated
├── Previous deployment available? → Switch traffic
│   ├── Health check passes? → Rollback successful
│   └── Health check fails? → ESCALATE to human
└── No previous deployment? → ESCALATE to human
```
