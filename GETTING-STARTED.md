# AES — Getting Started

You have a project. You want an AI agent to help you work on it — deploying, testing, training models, whatever. AES gives the agent a structured playbook so it knows what to do, instead of you explaining everything from scratch every session.

This guide walks you through the full workflow from zero.

---

## What You'll End Up With

```
my-project/
  .agent/                     # The agent's playbook
    agent.yaml                # Project identity — name, skills, dependencies
    instructions.md           # Master instructions for the agent
    permissions.yaml          # What the agent is allowed to do
    skills/                   # Step-by-step runbooks for specific tasks
      ORCHESTRATOR.md         # How skills connect together
      deploy.skill.yaml       # Skill metadata (for tooling)
      deploy.md               # Skill runbook (for the agent to read)
    workflows/                # State machines — what states things go through
    commands/                 # Slash commands (like /setup, /deploy)
    memory/                   # What the agent remembers across sessions
  .agentignore                # Files the agent should never touch
  CLAUDE.md                   # Auto-generated from .agent/ (for Claude)
  .cursorrules                # Auto-generated from .agent/ (for Cursor)
```

The `.agent/` directory is the source of truth. The tool-specific files (`CLAUDE.md`, `.cursorrules`, etc.) are auto-generated from it.

---

## Step 1: Install the CLI

```bash
pip install aes-cli
```

Or from source if you have the repo:

```bash
cd cli && pip install -e .
```

Verify:

```bash
aes --help
```

---

## Step 2: Initialize Your Project

Navigate to your project and run:

```bash
cd my-project
aes init
```

That's it. The CLI auto-detects your project name (from the directory) and language (from files like `package.json`, `pyproject.toml`, `go.mod`, etc.).

You'll see the scaffolded structure printed out, and the agent config files (`CLAUDE.md`, `.cursorrules`) are auto-generated.

### Pick a domain for pre-built skills

If your project fits a known domain, tell `aes init` and it will scaffold domain-specific skills, workflows, and instructions:

```bash
# Machine learning project — full 7-stage pipeline (discover, examine, train, classify, evaluate, package, publish)
aes init --domain ml

# Web application — gives you scaffold, test, deploy skills
aes init --domain web

# Infrastructure / DevOps — gives you provision, deploy, rollback skills
aes init --domain devops
```

Without `--domain`, the CLI auto-detects your framework (FastAPI, Next.js, Django, Rails, etc.) and generates framework-aware scaffolding with relevant skills and configurations. If no framework is detected, you get a generic scaffold that you fill in yourself.

### Initialize from a shared template

Instead of scaffolding from scratch, you can initialize from a template published to the registry — a complete `.agent/` configuration shared by your team or the community:

```bash
# From the registry
aes init --from aes-hub/ml-pipeline@^2.0

# From a local tarball
aes init --from ./ml-pipeline-2.1.0.tar.gz
```

This downloads the template's `.agent/` directory, extracts it into your project, and runs `aes sync` automatically.

### More options

```bash
# Override the project name
aes init --name my-cool-app

# Skip workflows if you don't need state machines
aes init --no-workflows

# Force a specific language
aes init --language python
```

### MCP Integration

`aes init` also generates a `.mcp.json` config file, which lets MCP-compatible tools (Claude Desktop, etc.) automatically discover the `aes-mcp` server. The MCP server exposes registry operations — search, install, publish — as tools the agent can call directly.

```bash
# Install with MCP support
pip install aes-cli[mcp]

# Or from source
cd cli && pip install -e ".[mcp]"
```

---

## Step 3: Let the Agent Fill It In

After `aes init`, the files have placeholder content (`<!-- AGENT: ... -->` comments and TODOs). You don't have to fill these in by hand — **the agent does it for you**.

Start your AI tool (Claude, Cursor, etc.) and run the setup command:

```
/setup
```

The agent runs a 7-phase process:

1. **Understand the project** — reads your code, README, package config, directory structure
2. **Fill instructions** — writes `instructions.md` with your project's architecture, rules, and workflows
3. **Define skills** — creates skill manifests and runbooks based on what your project actually does
4. **Define workflows** — maps out entity lifecycles (if applicable)
5. **Set permissions** — extracts allowed commands from your scripts and build tools
6. **Configure environment** — finds env vars from your code
7. **Validate and sync** — runs `aes validate` and `aes sync`

If the project is empty (no source code yet), the agent interviews you instead — asks what you're building, what tech stack, what operations it performs — then generates everything from your answers.

### What if I want to do it manually?

You can. The files are just YAML and Markdown. Here's what each one does:

| File | What It Controls |
|------|-----------------|
| `instructions.md` | Master playbook — project description, rules, architecture, gotchas |
| `skills/*.skill.yaml` | Skill metadata — inputs, outputs, dependencies (for tooling) |
| `skills/*.md` | Skill runbooks — step-by-step instructions (for the agent to follow) |
| `permissions.yaml` | What the agent is allowed to do (allow, deny, confirm) |
| `workflows/*.yaml` | State machines — what states things go through |
| `skills/ORCHESTRATOR.md` | How skills connect together and in what order |

Most people run `/setup` first, then manually tweak whatever the agent got wrong.

---

## Step 4: Sync to Your Tools

AES is tool-agnostic. It generates config files for whatever AI tool you use:

```bash
aes sync
```

This reads your `.agent/` directory and generates:

| Tool | Generated File |
|------|---------------|
| Claude | `CLAUDE.md` |
| Cursor | `.cursorrules` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Windsurf | `.windsurfrules` |

**You edit `.agent/`, then run `aes sync`.** Don't edit the generated files directly — they'll be overwritten.

### Check if you need to sync

```bash
aes status
```

This tells you if `.agent/` has changed since the last sync.

---

## Step 5: Validate

Make sure everything is well-formed:

```bash
aes validate
```

This checks:
- `agent.yaml` matches the schema
- All referenced files exist (skill manifests, runbooks, workflows)
- Skill dependencies are valid (no circular deps, no dangling references)
- Permissions are well-formed

Fix any errors before continuing.

---

## Step 6: Use It

Start your AI tool and it picks up the generated config automatically. The agent now knows:
- What your project is and how it's structured
- What it's allowed to do (and what it must never do)
- What skills it has and how to execute them step by step
- What state things are in (workflows)
- What it learned in previous sessions (memory)

You work normally — ask the agent to write code, fix bugs, deploy, whatever. The difference is that it has context and guardrails instead of starting from scratch every time.

### Slash commands

Commands you defined in `.agent/commands/` are available as slash commands:

```
/setup     — Auto-populate .agent/ config (run this first on a new project)
/deploy    — Deploy the application
```

---

## Step 7: Install Skills from the Registry (Optional)

If your team runs an AES registry, you can install pre-built skills instead of writing everything from scratch.

### Set up the registry connection

```bash
# Add to your ~/.zshrc or ~/.bashrc
export AES_REGISTRY_URL=https://registry.yourcompany.com
```

No auth token needed for installing — only for publishing.

### Browse what's available

```bash
aes search                  # list everything
aes search "deploy"         # search by keyword
aes search --tag ml         # filter by tag
aes search --domain devops  # filter by domain
aes search --type template  # only templates
aes search --type skill     # only skills
```

### Install a skill

```bash
aes install aes-hub/deploy@^1.0.0
```

This downloads the skill and puts it in `.agent/skills/vendor/`:

```
.agent/skills/
  vendor/
    aes-hub/
      deploy/
        skill.yaml
        runbook.md
  deploy.skill.yaml       # your own skills
  deploy.md
```

### Declare dependencies in agent.yaml

Instead of installing manually, declare what you need:

```yaml
# .agent/agent.yaml
dependencies:
  skills:
    "aes-hub/deploy": "^1.0.0"
    "aes-hub/monitoring": "~2.0.0"
```

Then install everything at once:

```bash
aes install
```

### Version specifiers

| Write this | Means |
|-----------|-------|
| `1.2.3` | Exactly 1.2.3 |
| `^1.2.0` | Any 1.x.x >= 1.2.0 (recommended for most cases) |
| `~1.2.0` | Any 1.2.x (patch updates only) |
| `>=1.0.0` | 1.0.0 or higher |
| `*` | Latest available |

---

## Step 8: Publish Your Skills (Optional)

If you wrote a skill that others on your team could use, publish it.

### Get a publish token

Ask your registry admin for a token. Set it:

```bash
export AES_REGISTRY_KEY=aes_tok_...
```

### Publish a skill

```bash
# Make sure it validates first
aes validate

# Publish a specific skill
aes publish --skill deploy --registry -o ./dist
```

### Publish a template

You can also share your entire `.agent/` configuration as a template — so others can bootstrap new projects from your setup:

```bash
aes publish --template --registry -o ./dist
```

By default, `memory/`, `local.yaml`, and `overrides/` are excluded (they contain sensitive/local data). Override with:

```bash
aes publish --template --include-memory     # include memory/
aes publish --template --include-all        # include everything
aes publish --template --exclude "secrets/**"  # add custom exclusions
```

### Versioning

Bump the version in your `.skill.yaml` (for skills) or `agent.yaml` (for templates) before publishing:

```yaml
version: "1.0.0"    # → "1.1.0" for new features, "2.0.0" for breaking changes
```

Published versions are **permanent** — you can't overwrite `1.0.0` once it's published. This is intentional. Everyone who installed `deploy@1.0.0` is guaranteed to have the exact same thing.

---

## The Full Loop

### First time (new project)

```
1. aes init --domain ml        (scaffold .agent/ with domain defaults)
2. Start your AI tool          (Claude, Cursor, etc.)
3. /setup                      (agent reads your code and fills in the config)
4. Review and tweak            (adjust anything the agent got wrong)
5. aes validate                (check everything is valid)
6. aes sync                    (regenerate tool configs with your tweaks)
```

### Day-to-day

```
1. Edit .agent/ files          (instructions, skills, permissions)
2. aes validate                (check everything is valid)
3. aes sync                    (regenerate CLAUDE.md, .cursorrules, etc.)
4. Start your AI tool          (it reads the generated config)
5. Work with the agent         (it follows your skills and instructions)
6. Agent updates memory        (what it learned goes into .agent/memory/)
7. Repeat
```

And occasionally:

```
aes install                    (grab updated skills from the registry)
aes publish --registry         (share your skills with the team)
aes publish --template --registry  (share your entire .agent/ config)
aes status                     (check if you need to sync)
```

---

## Quick Reference

| Command | What It Does |
|---------|-------------|
| `aes init` | Scaffold `.agent/` directory in your project |
| `aes init --domain ml` | Scaffold with ML-specific skills and workflows |
| `aes validate` | Check all files are valid and consistent |
| `aes sync` | Generate tool configs (CLAUDE.md, .cursorrules, etc.) |
| `aes status` | Check if `.agent/` changed since last sync |
| `aes inspect` | Show project structure and stats |
| `aes search "query"` | Search the skill registry |
| `aes search --type template` | Search for templates only |
| `aes install aes-hub/name@^1.0` | Install a skill from the registry |
| `aes install` | Install all dependencies from agent.yaml |
| `aes init --from aes-hub/name@^1.0` | Initialize project from a shared template |
| `aes publish --skill X --registry` | Publish a skill to the registry |
| `aes publish --template --registry` | Publish entire `.agent/` as a template |

---

## Troubleshooting

**`aes init` says the directory already exists**
It found an existing `.agent/`. Either delete it first or confirm the overwrite prompt.

**`aes validate` reports errors**
Read the error messages — they tell you exactly which file has the problem and what's wrong (missing field, bad format, dangling reference).

**`aes sync` doesn't generate anything**
Make sure `.agent/agent.yaml` exists and is valid. Run `aes validate` first.

**`aes search` returns nothing**
Either the registry is empty (nobody has published yet) or `AES_REGISTRY_URL` isn't set.

**Installed skill has a "depends_on references skill not in this project" warning**
The skill you installed depends on another skill you don't have. Install the missing dependency:
```bash
aes install aes-hub/missing-skill@^1.0.0
```

**The agent doesn't seem to use my changes**
Did you run `aes sync`? The AI tools read the generated files (`CLAUDE.md`, `.cursorrules`), not `.agent/` directly. You need to sync after every change.
