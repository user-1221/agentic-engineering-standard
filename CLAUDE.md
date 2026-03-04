# Agentic Engineering Standard (AES) — Agent Instructions

This repo defines the open standard for structuring, sharing, and discovering agentic engineering projects. It contains the specification, JSON schemas for validation, an `aes` CLI tool, and reference examples.

## Quick Reference

```bash
# Development
cd cli && pip install -e ".[dev]"     # install CLI in dev mode
python -m pytest cli/tests/ -v        # run tests
aes validate examples/ml-pipeline     # validate an example
aes validate templates/ml             # validate a template

# Working with the spec
ls spec/                              # all spec documents
ls schemas/                           # JSON schemas for validation
ls examples/                          # reference implementations
ls templates/                         # domain templates (ml, web, devops)
```

## Project Structure

```
spec/                    # The specification (10 documents + README)
schemas/                 # JSON Schemas for validating .agent/ files
cli/                     # The `aes` CLI tool (Python 3.9+)
  aes/
    commands/            # CLI commands: init, validate, inspect, publish, install, sync, status, search
    scaffold/            # Jinja2 templates for `aes init`
    targets/             # Sync adapters (claude, cursor, copilot, windsurf)
    validator.py         # Schema validation engine + dependency graph checks
    registry.py          # Registry client (fetch, resolve, download, upload, search)
    domains.py           # Domain-specific configs for init templates
  tests/                 # pytest suite
examples/                # Reference implementations
  ml-pipeline/           # ML Model Factory restructured as AES
  web-app/               # Web application agent system
  devops/                # DevOps agent system
templates/               # Dogfooded domain templates (validated AES packages)
  ml/                    # ML pipeline template (discover, examine, train)
  web/                   # Web app template (scaffold, test, deploy)
  devops/                # DevOps template (provision, deploy, rollback)
```

## Critical Rules

1. **Python 3.9** — use `from __future__ import annotations` everywhere. Pydantic uses `Optional[X]` from typing, not `X | None`.
2. **Spec is the source of truth** — schemas and CLI derive from the spec, not the other way around.
3. **Tool-agnostic** — the standard uses `.agent/` not `.claude/`. Never reference a specific AI tool in the spec except in `overrides` sections.
4. **YAML for humans, JSON Schema for machines** — all agent config is YAML. Validation schemas are JSON Schema draft 2020-12.
5. **Backward compatible** — breaking changes bump the AES major version. Additive changes are minor.
6. **Examples must validate** — every example in `examples/` and template in `templates/` must pass `aes validate`.

## Key Principle

The standard treats agent instructions, skills, permissions, and memory as **first-class engineering artifacts** — equal in importance to code. AES standardizes these so they become portable, composable, and shareable.

## Common Gotchas

- Skill manifests (`.skill.yaml`) are separate from runbooks (`.md`). The manifest is for tooling; the runbook is for agent reasoning.
- `agent.yaml` references paths relative to `.agent/` directory, not project root.
- The `overrides` section in `permissions.yaml` is optional — only needed when the generic format is insufficient for a specific tool.
- Registry YAML is for agent understanding; runtime code (Python dicts, etc.) is for execution. They stay in sync by convention.
- `depends_on` and `blocks` in skill manifests are validated as warnings (not errors) — vendored skills may reference skills not present in the current project.
- The AES registry uses `urllib.request` (stdlib) — no `requests` or `httpx` dependency. Set `AES_REGISTRY_URL` to override the default registry, `AES_REGISTRY_KEY` for publish auth.
- `aes status` re-generates sync plans in memory and diffs against stored hashes — it does not write any files.
- `aes publish --template` excludes `memory/`, `local.yaml`, and `overrides/` by default — use `--include-memory` or `--include-all` to override.
- `aes init --from` accepts both registry sources (`aes-hub/name@^1.0`) and local tarballs (`./template.tar.gz`).
- Registry packages have a `type` field (`"skill"` or `"template"`). Packages without `type` default to `"skill"` for backward compatibility.
