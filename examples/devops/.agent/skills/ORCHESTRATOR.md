# Infra Autopilot — Orchestrator

## Deployment Pipeline

```
provision → configure → deploy → monitor → verify
```

## Service Status Flow

```
planned → provisioning → configured → deploying → deployed → monitored
                                          ↓            ↓
                                       failed      degraded → rollback → deployed
```

## Decision Tree

```
1. Provision infrastructure (Terraform)
   ├── Plan shows destructive changes? → STOP, confirm with user
   └── Plan is additive? → Apply
2. Configure services (Ansible)
   ├── Dry-run shows unexpected changes? → STOP, investigate
   └── Dry-run clean? → Apply
3. Deploy service (blue-green)
   ├── Health check fails? → Rollback immediately
   ├── Error rate > 1%? → Rollback immediately
   └── All healthy? → Mark deployed
4. Monitor for 5 minutes
   ├── Metrics degrade? → Rollback
   └── Stable? → Confirm deployment
```
