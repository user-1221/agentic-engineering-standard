# SaaS Dashboard — Agent Instructions

Full-stack SaaS analytics dashboard with authentication, subscription billing, and real-time WebSocket updates. Next.js frontend, Express API, PostgreSQL.

## Quick Reference

```bash
npm run dev                    # start dev server
npm run test                   # run test suite
npm run db:migrate             # run pending migrations
npm run deploy:staging         # deploy to staging
```

## Project Structure

```
src/
  app/                         # Next.js app router pages
  components/                  # React components
  api/                         # Express API routes
  lib/
    db/                        # Drizzle ORM + migrations
    auth/                      # NextAuth.js config
    billing/                   # Stripe integration
    ws/                        # WebSocket server
  hooks/                       # React hooks
tests/
  unit/                        # Component + utility tests
  integration/                 # API endpoint tests
  e2e/                         # Playwright tests
```

## Critical Rules

1. **TypeScript strict** — no `any` types, no `@ts-ignore`.
2. **Server components by default** — only use `'use client'` when needed.
3. **Drizzle ORM** — no raw SQL. Use query builder.
4. **Auth on every API route** — use `withAuth` middleware.
5. **Feature flags** — new features behind `FEATURE_*` env vars until stable.

## Primary Workflow: "Add a New Feature"

### Phase 1: Understand Requirements
What does the feature do? What data does it need? How does billing interact?

### Phase 2: Implement
Schema migration → API route → UI component → tests.

### Phase 3: Test (DO NOT SKIP)
Unit tests pass, integration tests pass, manual QA on staging.

### Phase 4: Deploy
Staging first, verify metrics, then production.

## Key Principle

Ship incrementally. Every feature has a migration, tests, and feature flag before going to production.
