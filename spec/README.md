# Agentic Engineering Standard (AES) v1.0

## What Is AES?

AES is an open standard for structuring agentic engineering projects. It defines how to organize agent instructions, skills, permissions, state machines, registries, and memory so they are portable across tools, shareable across teams, and discoverable across the ecosystem.

**The core insight**: In agentic systems, the agent instructions, skills, and configuration are as important as the code itself. They deserve a standard.

## The `.agent/` Directory

Every AES-conformant project has a `.agent/` directory at its root:

```
my-project/
  .agent/
    agent.yaml              # Manifest (the "package.json" of agentic engineering)
    instructions.md         # Master agent instructions
    skills/                 # Modular runbooks
      ORCHESTRATOR.md       # Sequences all skills
      deploy.skill.yaml     # Structured manifest
      deploy.md             # Agent-readable runbook
    registry/               # Extensible component definitions
    workflows/              # State machine definitions
    commands/               # Multi-phase workflow automation
    permissions.yaml        # Agent capability boundaries
    memory/                 # Persistent agent learning
    overrides/              # Tool-specific config (claude/, cursor/, etc.)
  AGENT.md                  # Public-facing agent description
  .agentignore              # Files agents should never touch
```

## Quick Start

```bash
pip install aes-cli
cd my-project
aes init                    # scaffold .agent/ directory
aes validate                # check files against schemas + dependency graph
aes sync                    # generate tool configs (Claude, Cursor, Copilot, Windsurf)
aes status                  # show what changed since last sync
aes inspect                 # show project structure and stats
aes search "deploy"         # search the skill registry
aes search --type template  # search for templates
aes install aes-hub/deploy  # install a skill from the registry
aes init --from aes-hub/ml-pipeline@^2.0  # init from a template
aes publish --registry      # publish skills to the registry
aes publish --template --registry  # publish .agent/ as a template
```

## Specification Documents

| # | Document | Defines |
|---|----------|---------|
| 01 | [Manifest](01-manifest.md) | `agent.yaml` — project identity, skills, deps |
| 02 | [Instructions](02-instructions.md) | `instructions.md` — master agent playbook |
| 03 | [Skills](03-skills.md) | Portable, shareable skill definitions |
| 04 | [Registries](04-registries.md) | Extensible component registries |
| 05 | [Workflows](05-workflows.md) | State machine definitions |
| 06 | [Permissions](06-permissions.md) | Agent capability boundaries |
| 07 | [Memory](07-memory.md) | Persistent agent learning |
| 08 | [Commands](08-commands.md) | Multi-phase workflow automation |
| 09 | [Sharing](09-sharing.md) | Publishing, versioning, dependencies (skills & templates) |
| 10 | [Agentignore](10-agentignore.md) | `.agentignore` format |

## Design Principles

1. **Tool-agnostic** — works with Claude, GPT, Cursor, Copilot, or any agent tool
2. **Domain-agnostic** — ML, web dev, DevOps, data pipelines, anything
3. **Composable** — skills can be shared and installed independently
4. **Config over code** — agents change config, not orchestration logic
5. **Explicit over implicit** — state machines, permissions, and decisions are declared, not hidden in code

## Origin

AES was extracted from the [ML Model Factory](https://github.com/hiro/model-factory) — a production agentic system that trains, evaluates, and serves ML models. Every pattern in this spec was battle-tested there first, then generalized for any domain.

### How Model Factory Maps to AES

| Model Factory | AES Standard |
|--------------|-------------|
| `CLAUDE.md` | `.agent/instructions.md` |
| `skills/MASTER.md` | `.agent/skills/ORCHESTRATOR.md` |
| `skills/01_discover.md` | `.agent/skills/discover.md` + `discover.skill.yaml` |
| `config/model_registry.py` | `.agent/registry/models.yaml` |
| `config/metrics.py` | `.agent/registry/metrics.yaml` |
| Status tracking in `db/models.py` | `.agent/workflows/pipeline.yaml` |
| `.claude/settings.local.json` | `.agent/permissions.yaml` |
| `.claude/commands/train.md` | `.agent/commands/train.md` |
| `.claude/projects/.../memory/` | `.agent/memory/` |
