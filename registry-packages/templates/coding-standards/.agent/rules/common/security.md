---
name: security
scope: common
priority: critical
overridable_fields:
  - dependency_scan_frequency
defaults:
  dependency_scan_frequency: "weekly"
---

# Security Standards

## No Hardcoded Secrets
- Never commit API keys, tokens, passwords, or connection strings to source control
- Use environment variables or a secrets manager for all credentials
- Add secret patterns to `.gitignore` and use pre-commit hooks to detect leaks
- Rotate any credential that has been accidentally committed, even if the commit was reverted

## Input Validation
- Validate and sanitize all external input at system boundaries
- Use allowlists over denylists where possible
- Parameterize all database queries — never interpolate user input into SQL
- Validate file paths to prevent directory traversal attacks
- Set strict limits on request body size and upload file size

## Dependency Scanning
- Run dependency vulnerability scans ${dependency_scan_frequency}
- Pin dependency versions in lock files — do not use floating ranges in production
- Review changelogs before upgrading major versions
- Remove unused dependencies promptly

## Authentication and Authorization
- Use established libraries for auth — never roll your own crypto
- Enforce the principle of least privilege for all service accounts and API tokens
- Log authentication failures for monitoring; never log credentials themselves
- Set reasonable session timeouts and token expiration windows

## Data Protection
- Encrypt sensitive data at rest and in transit
- Avoid logging personally identifiable information (PII)
- Apply data retention policies — do not store data longer than necessary
