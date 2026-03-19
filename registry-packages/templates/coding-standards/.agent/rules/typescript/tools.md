---
name: tools
scope: typescript
priority: medium
---

# TypeScript Tooling

## ESLint
- Use `@typescript-eslint/parser` and `@typescript-eslint/eslint-plugin`
- Enable recommended rulesets: `eslint:recommended`, `plugin:@typescript-eslint/recommended`
- Enforce `no-unused-vars` (with `argsIgnorePattern: "^_"` for intentionally unused parameters)
- Run `eslint --fix` as part of the pre-commit hook

## Prettier
- Use Prettier for all formatting — do not configure formatting rules in ESLint
- Standard config: `printWidth: 100`, `singleQuote: true`, `trailingComma: "all"`
- Format on save in the editor; enforce via CI with `prettier --check`

## TypeScript Compiler
- Compile with `tsc --strict` — treat compiler warnings as errors in CI
- Enable `noUncheckedIndexedAccess` to catch unsafe array/object lookups
- Use project references (`composite: true`) for monorepo builds
- Keep `target` and `lib` aligned with the minimum supported Node.js or browser version

## Package Management
- Use a lock file (`package-lock.json`, `pnpm-lock.yaml`, or `yarn.lock`) — commit it
- Prefer `pnpm` or `npm` over `yarn` for new projects
- Run `npm audit` (or equivalent) in CI to catch known vulnerabilities
