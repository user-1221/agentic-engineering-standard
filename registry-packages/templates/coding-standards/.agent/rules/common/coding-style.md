---
name: coding-style
scope: common
priority: high
overridable_fields:
  - max_line_length
  - indent
defaults:
  max_line_length: 100
  indent: "2 spaces for JS/TS/YAML, 4 spaces for Python/Go"
---

# Coding Style

## Naming Conventions
- Use descriptive, intention-revealing names for variables, functions, and classes
- Prefer full words over abbreviations (`customerCount` not `custCnt`)
- Boolean variables start with `is`, `has`, `can`, or `should` (e.g. `isValid`, `hasPermission`)
- Constants use UPPER_SNAKE_CASE
- Functions and methods use verbs: `calculateTotal`, `fetchUser`, `validateInput`

## Formatting
- Maximum line length: ${max_line_length} characters
- Indentation: ${indent}
- One blank line between logical sections within a function
- Two blank lines between top-level declarations (classes, functions)
- No trailing whitespace

## Comments
- Write comments that explain **why**, not **what** — the code should explain what
- Use doc comments on all public APIs (functions, classes, modules)
- Mark incomplete work with `TODO(author):` and a brief explanation
- Remove commented-out code before committing; version control is the archive
- Keep comments up to date when modifying the associated code

## File Organization
- One primary concept per file (one class, one module of related functions)
- Group imports: stdlib first, then external, then internal — separated by blank lines
- Keep files under 300 lines; extract helpers when they grow beyond this
