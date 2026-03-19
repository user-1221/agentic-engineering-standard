---
name: security
scope: common
priority: high
overridable_fields:
  - credential_handling
defaults:
  credential_handling: "never share"
---

# Security Standards

## Credential Handling
- ${credential_handling}
- Never log API keys, tokens, or passwords
- Use environment variables for all secrets

## Channel Isolation
- Do not share information from one channel in another unless explicitly asked
- Treat each messaging platform as a separate security context

## Data Minimization
- Only request data needed for the current task
- Do not persist sensitive data in memory files
