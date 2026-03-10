# Changelog

All notable changes to the Agentic Engineering Standard are documented here.

This project maintains two version tracks:
- **Spec** (`spec-vX.Y`) — the AES standard itself (spec documents, schemas, examples)
- **CLI** (`cli-vX.Y.Z`) — the `aes` command-line tool

## [Unreleased]

### CLI
- Add file-watching token reload for registry server
- Add private package support and `--visibility` flag to `aes publish`
- Add MCP server (`aes-mcp`) as core dependency
- Add `aes status` command for sync status diffing
- Add interactive target selection prompt to `aes sync`
- Add smart project detection (language, framework) to `aes init`
- Add Dev-Assist / Agent-Integrated mode picker to `aes init`
- Add Research domain to `aes init`
- Add workflow commands and operations memory scaffolding
- Sync skills as separate Claude slash commands under `.claude/commands/skills/`
- Fall back to DEV_ASSIST_BASE_CONFIG for unknown domains
- Bump minimum Python to 3.10+

### Spec
- Add AES file format reference to instructions.md template
- Add workflow command runbooks and operations.md stage tracker
- Unify operations.md into chronological log with Read Cursor

## [cli-v0.1.0] — 2026-03-04

Initial release of the AES CLI.

### Added
- `aes init` — scaffold an AES project (ML, Web, DevOps domains)
- `aes validate` — validate `.agent/` files against JSON Schemas
- `aes inspect` — inspect AES project structure
- `aes sync` — sync to tool-specific formats (Claude, Cursor, Copilot, Windsurf)
- `aes publish` — publish skills/templates to AES registry
- `aes install` — install skills from registry or local tarballs
- `aes search` — search the AES registry

## [spec-v1.0] — 2026-03-04

Initial release of the Agentic Engineering Standard.

### Added
- 10 specification documents (01-manifest through 10-llm-context)
- JSON Schemas for agent, skill, workflow, registry, permissions (draft 2020-12)
- 3 reference examples (ml-pipeline, web-app, devops)
- 3 domain templates (ml, web, devops)
- Semver-based version resolution for registry packages
