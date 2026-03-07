# Skill: Code Review

## Purpose

Run automated code quality checks: linting, type checking, bundle size analysis, and security scanning.

## When to Run

- After all tests pass
- Before deployment to staging

## How It Works

1. Run ESLint with project rules
2. Run TypeScript type checker (strict mode)
3. Analyze bundle size for regressions
4. Run npm audit for security vulnerabilities
5. Collect all issues into a report

## Decision Tree

```
Run lint:
  ├── Errors? → Fix before continuing
  └── Clean? → Run typecheck
      ├── Type errors? → Fix before continuing
      └── Clean? → Check bundle size
          ├── >10% increase? → Investigate, optimize
          └── Acceptable? → Run security scan
              ├── Critical vulns? → Fix before deploy
              └── Clean? → Review passed
```

## Error Handling

- **Lint errors**: Must fix, cannot deploy with lint errors
- **Type errors**: Must fix, strict mode is non-negotiable
- **Security vulnerability**: Critical = block, moderate = warn
