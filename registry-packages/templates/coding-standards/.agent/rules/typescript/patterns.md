---
name: patterns
scope: typescript
priority: high
---

# TypeScript Patterns

## Prefer `const`
- Default to `const` for all declarations; use `let` only when reassignment is necessary
- Never use `var` — it has function scope and hoisting, which cause subtle bugs
- Use `as const` for literal types and frozen configuration objects

## Strict Mode
- Enable `strict: true` in `tsconfig.json` — this includes `strictNullChecks`, `noImplicitAny`, and all other strict flags
- Never use `any` as a type escape hatch; prefer `unknown` and narrow with type guards
- Avoid non-null assertions (`!`) except when interfacing with external APIs that lack proper types

## Error Handling
- Define custom error classes that extend `Error` for domain-specific failures
- Use discriminated unions for result types when errors are expected (e.g. `Result<T, E>`)
- Always type `catch` blocks — use `unknown` and narrow before accessing properties
- Prefer early returns to reduce nesting in error-handling code

## Type Design
- Export interfaces for public API contracts; use `type` aliases for unions and utility types
- Prefer `interface` over `type` for object shapes — interfaces are open for declaration merging
- Avoid enum at module boundaries; prefer string literal unions for serialization safety
- Use generics to eliminate duplication, but keep type parameters to three or fewer
