# Agentic Engineering Standard (AES) — Agent Instructions

This repo defines the open standard for structuring, sharing, and discovering agentic engineering projects. It contains the specification, JSON schemas for validation, an `aes` CLI tool, and reference examples.

## Quick Reference

```bash
# Development (use existing venv or create one)
cd cli && python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"              # install CLI in dev mode
python -m pytest tests/ -v           # run tests
aes validate examples/ml-pipeline    # validate an example
aes validate templates/ml            # validate a template

# Working with the spec
ls spec/                              # all spec documents
ls schemas/                           # JSON schemas for validation
ls examples/                          # reference implementations
ls templates/                         # domain templates (ml, web, devops, research, assistant)
```

## Project Structure

```
spec/                    # The specification (10 documents + README)
schemas/                 # JSON Schemas for validating .agent/ files
cli/                     # The `aes` CLI tool (Python 3.10+)
  aes/
    commands/            # CLI commands: init, validate, inspect, publish, install, sync, status, search
    scaffold/            # Jinja2 templates for `aes init`
    targets/             # Sync adapters (claude, cursor, copilot, windsurf, openclaw)
    validator.py         # Schema validation engine + dependency graph checks
    registry.py          # Registry client (fetch, resolve, download, upload, search)
    domains.py           # Domain-specific configs for init templates (ml, web, devops, research)
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

1. **Python 3.10** — use `from __future__ import annotations` everywhere. Pydantic uses `Optional[X]` from typing, not `X | None`.
2. **Spec is the source of truth** — schemas and CLI derive from the spec, not the other way around.
3. **Tool-agnostic** — the standard uses `.agent/` not `.claude/`. Never reference a specific AI tool in the spec except in `overrides` sections.
4. **YAML for humans, JSON Schema for machines** — all agent config is YAML. Validation schemas are JSON Schema draft 2020-12.
5. **Backward compatible** — breaking changes bump the AES major version. Additive changes are minor.
6. **Examples must validate** — every example in `examples/` and template in `templates/` must pass `aes validate`.

## Key Principle

The standard treats agent instructions, skills, permissions, and memory as **first-class engineering artifacts** — equal in importance to code. AES standardizes these so they become portable, composable, and shareable.

## Versioning

Two version tracks, bumped independently:
- **Spec** (`X.Y`) — the standard itself. Bump on spec, schema, or example changes.
- **CLI** (`X.Y.Z`, semver) — the `aes` tool. Bump on CLI changes.

```bash
python scripts/bump-version.py --cli 0.2.0 --dry-run   # preview
python scripts/bump-version.py --cli 0.2.0              # update files
# edit CHANGELOG.md, then commit, then run the printed git tag commands
```

The script updates version strings across all files (pyproject.toml, __init__.py, spec/README.md, schemas, examples, templates, scaffolds). It prints `git tag` commands to run after committing.

## Workflow Rules

- **Document systematic changes** — when making architectural or infrastructure changes (e.g. changing how services communicate, modifying auth flows, updating deployment configs), update all relevant documentation: CLAUDE.md, MEMORY.md, deploy.md, README files, and architecture docs. Don't leave docs stale.

## Common Gotchas

- Skill manifests (`.skill.yaml`) are separate from runbooks (`.md`). The manifest is for tooling; the runbook is for agent reasoning.
- `agent.yaml` references paths relative to `.agent/` directory, not project root.
- The `overrides` section in `permissions.yaml` is optional — only needed when the generic format is insufficient for a specific tool.
- Registry YAML is for agent understanding; runtime code (Python dicts, etc.) is for execution. They stay in sync by convention.
- `depends_on` and `blocks` in skill manifests are validated as warnings (not errors) — vendored skills may reference skills not present in the current project.
- The AES registry uses `urllib.request` (stdlib) — no `requests` or `httpx` dependency. Set `AES_REGISTRY_URL` to override the default registry, `AES_REGISTRY_KEY` for publish auth.
- `aes sync` prompts for target selection interactively; use `-t claude` (or cursor/copilot/windsurf/openclaw) to skip the prompt. In non-interactive mode (CI), defaults to all targets. Targets that fail validation (e.g. openclaw on a project without `identity`/`model`) are silently skipped when syncing all targets.
- For Claude, skills are synced as separate files under `.claude/commands/skills/<id>.md` (slash commands), not inlined into CLAUDE.md. CLAUDE.md only has a skill index. Other targets (cursor, copilot, windsurf) still inline skill runbooks since they don't support separate command files.
- `aes init` uses a two-step interactive picker: first choose mode (Dev-Assist vs Agent-Integrated), then choose project type. Dev-Assist (agent builds the project, then steps back): API, Web, CLI, Library, DevOps. Agent-Integrated (agent is embedded in the running product): ML, Research, Assistant, Custom.
- Domain configs have `mode` ("dev-assist" or "agent-integrated") and `workflow_commands` (list of `CommandDef`). ML and Research are agent-integrated; Web and DevOps are dev-assist.
- Each domain scaffolds a workflow command runbook (e.g. `/train`, `/build`, `/process`, `/provision`) under `.agent/commands/`. These reference `.agent/memory/operations.md` for pipeline state tracking.
- When a domain has a workflow, `aes init` creates `.agent/memory/operations.md` — a stage progress tracker the agent updates as it runs the pipeline.
- `aes status` re-generates sync plans in memory and diffs against stored hashes — it does not write any files.
- `aes publish --template` excludes `memory/`, `local.yaml`, and `overrides/` by default — use `--include-memory` or `--include-all` to override.
- `aes init --from` accepts both registry sources (`aes-hub/name@^1.0`) and local tarballs (`./template.tar.gz`).
- Registry packages have a `type` field (`"skill"` or `"template"`). Packages without `type` default to `"skill"` for backward compatibility.
- `aes publish --registry` prompts for visibility (public/private) interactively; use `--visibility public` or `--visibility private` to skip. In non-interactive mode (CI), defaults to public. Registry packages have a `visibility` field (`"public"` or `"private"`). Packages without `visibility` default to `"public"` for backward compatibility. Private packages require `AES_REGISTRY_KEY` to search/download.
- **OpenClaw target**: `aes sync -t openclaw` requires `identity` and `model` sections in `agent.yaml` (sync-time enforcement, not schema-time). Use `aes init --domain assistant` to scaffold them. The target generates `.openclaw/` with `openclaw.json`, workspace Markdown files (SOUL.md, IDENTITY.md, USER.md, HEARTBEAT.md, AGENTS.md, MEMORY.md, TOOLS.md), SKILL.md files in `workspace/skills/<id>/`, and OpenShell `policy.yaml` when `sandbox.runtime == "openshell"`. Environment variables use `${VAR}` interpolation — never hardcoded.
- The `assistant` domain config adds `identity`, `model`, `heartbeat`, and `channels` sections to `agent.yaml` scaffolds. These are standard AES fields consumed by the openclaw target but ignored by other targets.
- `SkillDef` dataclass has OpenClaw-specific optional fields: `emoji`, `requires_bins`, `requires_env`, `primary_env`, `user_invocable`, `license_id`, `mcp_server`. These have defaults so existing ML/Web/DevOps/Research configs are unaffected.
- JSON schemas in `schemas/` must be kept in sync with `cli/aes/schemas/`. When updating schemas, copy from `schemas/` to `cli/aes/schemas/`.
