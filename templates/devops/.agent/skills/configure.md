# Skill: Configure Service

## Purpose

Apply service configuration using Ansible playbooks after infrastructure is provisioned.

## When to Run

- Infrastructure provisioned (Terraform applied)
- Configuration changes needed
- New service setup

## How It Works

1. Run `ansible-playbook --check` for dry-run preview
2. Review changes for unexpected modifications
3. Apply configuration with `ansible-playbook`
4. Verify services are running with correct config
5. Advance to `configured`

## Decision Tree

```
Dry-run playbook:
  ├── No changes? → Skip (already configured)
  ├── Expected changes only? → Apply
  ├── Unexpected changes? → STOP, investigate
  └── After apply:
      ├── Service healthy? → Status: configured
      └── Service unhealthy? → Rollback config, investigate
```

## Error Handling

- **Vault password missing**: Abort, cannot decrypt secrets
- **Playbook error**: Fix playbook before retrying
- **Service unhealthy after config**: Rollback to previous config
