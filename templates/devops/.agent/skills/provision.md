# Skill: Provision Infrastructure

## Purpose

Create or update cloud infrastructure using Terraform.

## When to Run

- New service needs infrastructure
- Existing service needs scaling or config change

## How It Works

1. `terraform plan -out=plan.tfplan` — preview all changes
2. Review plan for destructive actions (destroy, replace)
3. `terraform apply plan.tfplan` — apply only after review
4. Verify resources created via `terraform state list`

## Decision Tree

```
terraform plan
├── No changes? → Skip (already up to date)
├── Only additions? → Safe to apply
├── Modifications? → Review carefully, apply if benign
└── Destructions? → STOP — confirm with user before applying
```

## Error Handling

- **Plan error**: Fix config before proceeding
- **Apply error**: Check state, do NOT retry blindly
