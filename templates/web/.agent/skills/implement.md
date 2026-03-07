# Skill: Implement Feature

## Purpose

Implement the feature by writing migration logic, API routes, UI components, and wiring up the feature flag.

## When to Run

- After scaffold creates boilerplate files
- Feature requirements are clear

## How It Works

1. Write database migration (if needed)
2. Implement API route with business logic and auth middleware
3. Build React component (server-first, client when interactive)
4. Wire up feature flag for gradual rollout
5. Verify dev server runs without errors

## Decision Tree

```
For each scaffolded file:
  ├── Migration file? → Write schema changes, add rollback
  ├── API route? → Add business logic, input validation, auth
  ├── Component? → Implement UI, add loading/error states
  └── All files populated? → Run dev server to verify
```

## Error Handling

- **Type error**: Fix before moving to tests
- **Migration conflict**: Resolve with existing migrations
- **Dev server crash**: Check imports and dependencies
