# Agentic Engineering Standard (AES)

**The open standard for structuring, sharing, and discovering agentic engineering projects.**

AES does for agent systems what `package.json` did for Node.js — it standardizes how agent instructions, skills, permissions, state machines, and memory are organized so they become portable, composable, and shareable.

**New here?** Read the [Getting Started guide](GETTING-STARTED.md) — it walks through the full workflow from zero.

## The Problem

Every agentic project reinvents the same patterns: how to instruct the agent, how to define skills, how to track state, how to set permissions. There's no standard format, no way to share agent configurations, no registry to discover them.

## The Solution

A `.agent/` directory in every project:

```
my-project/
  .agent/
    agent.yaml              # Manifest — the "package.json" of agentic engineering
    instructions.md         # Master agent playbook
    skills/                 # Modular, shareable runbooks
      ORCHESTRATOR.md
      train.skill.yaml      # Structured manifest
      train.md              # Agent-readable runbook
    registry/               # Extensible component definitions
    workflows/              # State machine definitions
    commands/               # Slash commands (/setup, /train, /build, /process)
    permissions.yaml        # Agent capability boundaries
    memory/                 # Persistent agent learning
  .agentignore              # Files agents should never touch
```

## Quick Start

```bash
# Install the CLI
cd cli && pip install -e .

# Scaffold a new AES project
aes init

# Validate your .agent/ directory
aes validate

# Generate tool-specific configs (prompts you to pick your tool)
aes sync

# Check what changed since last sync
aes status

# Search the registry
aes search "deploy"
aes search --type template

# Install a skill from the registry
aes install aes-hub/deploy@^1.0.0

# Initialize from a shared template
aes init --from aes-hub/ml-pipeline@^2.0

# Publish a skill
aes publish ./my-skill -o dist/

# Publish a complete .agent/ config as a template
aes publish --template --registry -o dist/              # public by default
aes publish --skill train --registry --visibility private  # private package
```

## Specification

The full spec is in [`spec/`](spec/):

| # | Document | What It Defines |
|---|----------|-----------------|
| 01 | [Manifest](spec/01-manifest.md) | `agent.yaml` — identity, skills, deps, environment |
| 02 | [Instructions](spec/02-instructions.md) | `instructions.md` — master agent playbook |
| 03 | [Skills](spec/03-skills.md) | Portable skill definitions (manifest + runbook) |
| 04 | [Registries](spec/04-registries.md) | Extensible component catalogs |
| 05 | [Workflows](spec/05-workflows.md) | State machine definitions |
| 06 | [Permissions](spec/06-permissions.md) | Agent capability boundaries |
| 07 | [Memory](spec/07-memory.md) | Persistent agent learning |
| 08 | [Commands](spec/08-commands.md) | Multi-phase workflow automation |
| 09 | [Sharing](spec/09-sharing.md) | Publishing, versioning, dependencies |
| 10 | [Agentignore](spec/10-agentignore.md) | `.agentignore` format |

## CLI Tool

The `aes` CLI (`cli/`) provides:

| Command | Description |
|---------|-------------|
| `aes init` | Scaffold a `.agent/` directory (two-step picker: mode + type, or auto-detect) |
| `aes validate [path]` | Validate files against JSON schemas + dependency graph checks |
| `aes inspect [path\|name]` | Show project structure (local) or registry package details (remote) |
| `aes sync [path]` | Generate tool-specific configs (prompts for target selection) |
| `aes status [path]` | Show what changed in `.agent/` since last sync |
| `aes publish [skill]` | Package skills as tarballs, optionally upload to registry (`--registry`) |
| `aes publish --template` | Package entire `.agent/` directory as a shareable template |
| `aes install [source]` | Install skills from tarballs, local dirs, or the AES registry |
| `aes search [query]` | Search the AES package registry (supports `--sort-by`, `--limit`, `-v`) |

## MCP Server

The `aes-mcp` command exposes the AES registry as a [Model Context Protocol](https://modelcontextprotocol.io/) tool server, letting MCP-compatible agents search, install, and publish packages directly.

```bash
# Install with MCP extras
cd cli && pip install -e ".[mcp]"

# Run the MCP server
aes-mcp
```

`aes init` auto-generates a `.mcp.json` config file so MCP-compatible tools discover the server automatically.

## Web Dashboard

A GitHub OAuth dashboard for managing registry API tokens lives in `web/`. It provides a self-service UI at `aes-official.com` where users authenticate with GitHub and create/revoke tokens for `aes publish`.

## Examples & Templates

Three reference implementations in [`examples/`](examples/) and installable domain templates in [`templates/`](templates/):

| Example | Domain | Mode | Skills | Workflow Command |
|---------|--------|------|--------|-----------------|
| [ml-pipeline](examples/ml-pipeline/) | Machine Learning | Agent-Integrated | discover, examine, train, ... | `/train` |
| [web-app](examples/web-app/) | Web Development | Dev-Assist | scaffold, test, deploy, ... | `/build` |
| [devops](examples/devops/) | Infrastructure | Dev-Assist | provision, deploy, rollback, ... | `/provision` |

The `templates/` directory contains validated AES skill packages that can be used as starting points for new projects. Templates have expanded skill suites — ML has a full 7-stage pipeline, web has 5 skills, devops has 5 skills, and the **research** domain has 5 skills for content processing pipelines (ingest, parse, analyze, organize, display).

### Modes

AES distinguishes two kinds of agentic projects:

- **Dev-Assist** — The agent builds the project (scaffold, implement, test, deploy). Once shipped, its main job is done — though it can still help with maintenance and bug fixes. (Web, API, CLI, Library, DevOps)
- **Agent-Integrated** — The agent is embedded in the running product. It operates continuously as part of the system — training models, processing content, ingesting data. The product doesn't work without it. (ML pipelines, Research pipelines)

`aes init` presents a two-step picker: choose mode, then choose project type. Each domain scaffolds a workflow command (e.g. `/train`, `/build`, `/process`) and an operations memory file for pipeline tracking.

## Registry

AES includes a package registry at `registry.aes-official.com` for sharing skills and templates:

```bash
# Search for skills and templates
aes search "deploy"
aes search --tag ml
aes search --domain devops
aes search --type template          # only templates
aes search --type skill             # only skills
aes search --sort-by version        # sort by semver (highest first)
aes search --limit 5 -v             # top 5, verbose (version count + date)

# Inspect a remote package
aes inspect deploy                  # latest version from registry
aes inspect deploy@1.0.0            # specific version

# Install a skill from registry
aes install aes-hub/deploy@^1.0.0

# Initialize a project from a shared template
aes init --from aes-hub/ml-pipeline@^2.0

# Publish a skill to registry (requires AES_REGISTRY_KEY)
aes publish --skill train --registry -o dist/

# Publish an entire .agent/ config as a template
aes publish --template --registry -o dist/
```

Version resolution supports: exact (`1.2.3`), caret (`^1.2.0`), tilde (`~1.2.0`), minimum (`>=1.0.0`), and wildcard (`*`).

### Templates vs Skills

| | Skill | Template |
|---|-------|----------|
| **What** | Single capability (manifest + runbook) | Complete `.agent/` configuration |
| **Install** | `aes install aes-hub/name@^1.0` | `aes init --from aes-hub/name@^1.0` |
| **Publish** | `aes publish --skill X --registry` | `aes publish --template --registry` |
| **Goes to** | `.agent/skills/vendor/` | `.agent/` (whole directory) |

Templates exclude `memory/`, `local.yaml`, and `overrides/` by default to protect sensitive data. Use `--include-memory` or `--include-all` to override.

## Design Principles

1. **Tool-agnostic** — works with Claude, GPT, Cursor, Copilot, or any agent
2. **Domain-agnostic** — ML, web, DevOps, research, data pipelines, anything
3. **Composable** — skills and templates are shareable independently
4. **Config over code** — agents modify configuration, not orchestration logic
5. **Explicit over implicit** — state machines, permissions, decisions are declared

## JSON Schemas

Validation schemas in [`schemas/`](schemas/) enable IDE autocompletion and CI validation:

- `agent.schema.json` — validates `agent.yaml`
- `skill.schema.json` — validates `*.skill.yaml`
- `workflow.schema.json` — validates workflow definitions
- `registry.schema.json` — validates component registries
- `permissions.schema.json` — validates `permissions.yaml`

## License

Apache 2.0 — see [LICENSE](LICENSE)
