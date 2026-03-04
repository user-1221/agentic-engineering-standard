# Skill: Run Tests

## Purpose

Run the full test suite to verify feature quality before deployment.

## How It Works

1. Unit tests: Jest + React Testing Library
2. Integration tests: Supertest against Express API
3. E2E tests: Playwright against running dev server

## Decision Tree

```
Run unit tests
├── Fails? → Fix before continuing
└── Passes? → Run integration tests
    ├── Fails? → Fix API route or middleware
    └── Passes? → Run e2e tests
        ├── Fails? → Fix UI interaction
        └── All pass? → Ready for deployment
```
