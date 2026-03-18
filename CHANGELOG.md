# Changelog

All notable changes to the Agentic Engineering Standard are documented here.

This project maintains two version tracks:
- **Spec** (`spec-vX.Y`) — the AES standard itself (spec documents, schemas, examples)
- **CLI** (`cli-vX.Y.Z`) — the `aes` command-line tool

## [Unreleased]

## [spec-v1.2] / [cli-v0.6.0] — 2026-03-18

### Added
- **AI Bill of Materials** (`bom.yaml`) — new spec doc (11-bom.md) and schema for tracking models, frameworks, tools, and data sources used by agents
- **Decision records** — structured decision records in `.agent/memory/decisions/*.yaml` with new spec doc (12-decision-records.md) and schema
- **Extended manifest** — `agent.yaml` gains `models`, `provenance`, and `interop` sections
- **Policy extensions** — `permissions.yaml` gains `network`, `process`, `inference`, and `data` policy sections
- **Package manifests** — `aes publish` generates `aes-manifest.json` with SHA256 digests
- `aes bom` command for generating and inspecting AI Bills of Materials
- `aes upgrade` command with 1.1→1.2 migration support
- `aes inspect` now displays extended manifest fields (models, provenance, interop)

### Changed
- `aes sync` (Claude target) only includes "Memory Management" section when the project declares a `/memory` command
- Bump spec version to 1.2, CLI version to 0.6.0
- Update website to v1.2: mobile hamburger nav, visual polish (card hover effects, gradient accents), improved Japanese translations
- Update GETTING-STARTED.md and README.md with BOM and decision record documentation

## [spec-v1.1] / [cli-v0.5.0] — 2026-03-17

### Added
- Add `/memory` command — cross-domain command that reviews conversation context and saves learnings to `.agent/memory/`. Scaffolded for all project types by `aes init`
- Add "Cross-Domain Commands" section to spec 08 (commands)
- Add `/memory` command documentation to spec 07 (memory), including lifecycle step 5
- Add "Memory Management" auto-trigger instruction to Claude sync target (CLAUDE.md)
- Add Japanese localization for `/memory` command runbook

### Changed
- Bump spec version to 1.1 (additive: new cross-domain command pattern)

## [cli-v0.4.3] — 2026-03-14

### Added
- Add `/build` command to all framework-based project types (API, Web app, CLI, Library, Frontend) — previously only domain types (ML, Web, DevOps, Research) and the generic fallback had workflow commands
- Add upgrade instructions to README, CLI README, and Getting Started guide

### Fixed
- Fix test suite locale isolation — tests now force `AES_LANG=en` via conftest fixture so they pass regardless of user's `~/.aes/config.yaml` locale setting

## [cli-v0.4.2] — 2026-03-14

### Changed
- Recommend `pipx` as primary install method across all docs, landing page, and CLI hints (PEP 668 compatibility)
- Keep `pip` as fallback for virtual environment users

## [cli-v0.4.1] — 2026-03-14

### Security
- Fix XSS in dashboard token revoke button (inline JS context)
- Fix path traversal in `aes sync` — validate all paths from agent.yaml before read/write
- Fix tarball extraction to reject symlinks and hardlinks
- Add registry URL validation to prevent SSRF via `AES_REGISTRY_URL`
- Restrict `PUT /index.json` to admin scope; server auto-updates index on package publish
- Fix IPv6 parsing in registry `clientIP()` — use `net.SplitHostPort` + `IsLoopback()`
- Use constant-time comparison for CSRF token validation
- Sanitize command/skill IDs in sync targets to prevent path separator injection
- Remove internal error details from user-facing messages (web + registry)
- Add `HttpOnly`/`Secure`/`SameSite` to OAuth state cookie clearing
- Wrap HTTP errors in CLI to prevent token leakage in tracebacks
- Add `.env`, `*.pem`, `*.key`, `secrets/**` to default publish exclusions
- Increase OAuth state entropy from 128-bit to 256-bit

### Changed
- Server auto-updates `index.json` on package publish via `X-AES-*` headers
- CLI no longer calls `PUT /index.json` directly — metadata sent as headers on package PUT

## [cli-v0.4.0] — 2026-03-14

### Added
- **i18n support**: First-run interactive language selection (English / Japanese)
- All CLI output (prompts, status messages, errors, labels) translated to Japanese
- Japanese scaffold templates for generated `.agent/` content (instructions, skills, orchestrator, commands, operations)
- Japanese domain configs for ML, Web, DevOps, and Research domains
- Global user config at `~/.aes/config.yaml` for persisting language preference
- Language override via `AES_LANG` environment variable or hidden `--lang` flag
- `aes inspect` supports remote registry packages (`aes inspect deploy`, `aes inspect deploy@1.0.0`)
- `aes search` adds `--sort-by` (name/latest/version), `--limit N`, and `--verbose`/`-v` options
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
