# Skill: Deploy Service

## Purpose

Deploy a service using blue-green strategy with health checks.

## When to Run

- Infrastructure provisioned
- New version ready to ship
- Staging verified (for production deploys)

## How It Works

1. Build new container image
2. Deploy to "green" target
3. Run health checks against green
4. Switch traffic from blue to green
5. Monitor for 5 minutes
6. Tear down old blue (or keep for rollback)

## Decision Tree

```
Deploy green instance
├── Build fails? → Abort, fix build
├── Health check fails? → Abort, keep blue
├── Traffic switch
│   ├── Error rate spikes? → Rollback to blue immediately
│   └── All healthy for 5 min? → Confirm deploy, tear down blue
```
