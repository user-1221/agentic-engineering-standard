# Infra Autopilot — Agent Instructions

Infrastructure automation for cloud services. Provision, configure, deploy, monitor, and rollback. Uses Terraform for infra, Ansible for config, and Docker for services.

## Quick Reference

```bash
terraform plan -out=plan.tfplan    # preview changes
terraform apply plan.tfplan         # apply changes
ansible-playbook -i inventory configure.yml
python scripts/manage.py deploy --service api --env staging
python scripts/manage.py rollback --service api --env staging
```

## Project Structure

```
terraform/         # Infrastructure as code
ansible/           # Configuration management
scripts/           # Deployment and management scripts
monitoring/        # Alerting rules and dashboards
docker/            # Dockerfiles and compose files
```

## Critical Rules

1. **Never apply without plan** — always `terraform plan` before `terraform apply`.
2. **Staging first** — every change hits staging before production.
3. **Rollback ready** — every deploy must have a rollback path tested.
4. **No hardcoded secrets** — use AWS Secrets Manager or Vault.
5. **Tag everything** — all resources tagged with service, env, owner, cost-center.

## Primary Workflow

### Phase 1: Verify Prerequisites
Check: image built, tests pass, staging healthy, rollback tested.

### Phase 2: Deploy to Staging
Blue-green deployment, health check, smoke tests.

### Phase 3: Monitor (DO NOT SKIP)
Watch error rates, latency p99, CPU/memory for 5 minutes.

### Phase 4: Promote or Rollback
If metrics stable -> promote to production. If metrics degrade -> immediate rollback.

## Key Principle

Infrastructure changes are permanent and visible. Measure twice, apply once. Always have a rollback plan.

## Common Gotchas

- Terraform state is shared — always run `terraform plan` to see what others changed.
- Ansible playbooks are NOT idempotent by default — test with `--check` first.
- Docker images must be tagged with git SHA — never use `latest` in production.
