---
name: git-workflow
scope: common
priority: high
overridable_fields:
  - branch_prefix
  - require_linear_history
defaults:
  branch_prefix: "feat/, fix/, chore/, docs/, refactor/"
  require_linear_history: true
---

# Git Workflow

## Branching Strategy
- Main branch (`main`) is always deployable
- Create feature branches from `main` using prefixes: ${branch_prefix}
- Keep branches short-lived — merge within a few days, not weeks
- Delete branches after merging

## Commit Messages
- Use conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`
- Keep the subject line under 72 characters
- Use imperative mood: "add feature" not "added feature" or "adds feature"
- Reference issue numbers in the body when applicable: `Closes #42`

## Pull Request Process
- PRs require at least one approval before merge
- PR title follows the same format as commit messages
- Include a summary of **what** changed and **why**
- Add a test plan or verification steps
- Keep PRs focused — one logical change per PR
- Address all review comments before merging

## History Hygiene
- Squash-merge feature branches into `main` to maintain a clean history
- Never force-push to `main` or shared branches
- Rebase feature branches onto `main` before merging to resolve conflicts
