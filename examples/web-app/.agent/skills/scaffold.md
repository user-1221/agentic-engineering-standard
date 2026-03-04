# Skill: Scaffold Feature

## Purpose

Generate all boilerplate files for a new feature: migration, API route, UI component, and test stubs.

## When to Run

- Starting a new feature
- User says "add feature X"

## How It Works

1. Create migration file if DB changes needed
2. Create API route with auth middleware
3. Create React component (server or client)
4. Create test files (unit + integration)
5. Update feature flag env var

## Code Location

- Generator: `plopfile.ts`
- Templates: `templates/`
