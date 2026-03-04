# 01 — Manifest: `agent.yaml`

The manifest is the entry point for any AES project. It declares what the agentic system is, what it can do, and where everything lives. It is the "package.json" of agentic engineering.

## Location

`.agent/agent.yaml` — always at this path, always this filename.

## Format

YAML with comments. Validated against `schemas/agent.schema.json`.

## Sections

### Identity

```yaml
aes: "1.0"                           # AES spec version

name: "my-agent-project"             # kebab-case, unique within registry
version: "1.0.0"                     # semver
description: "What this system does" # one-line summary
domain: "machine-learning"           # ml, web, devops, data-pipeline, etc.
license: "MIT"
repository: "https://github.com/user/repo"

author:
  name: "Author Name"
  email: "author@example.com"
```

**Required**: `aes`, `name`, `version`, `description`
**Optional**: `domain`, `license`, `repository`, `author`

### Runtime

```yaml
runtime:
  language: "python"                 # primary language
  version: "3.9"                     # minimum version
  entry_point: "scripts/run.py"      # main CLI entry point
  setup: "setup.sh"                  # setup script (optional)
```

**Required**: `language`
**Optional**: `version`, `entry_point`, `setup`

### Agent

```yaml
agent:
  instructions: "instructions.md"    # path relative to .agent/
  permissions: "permissions.yaml"
  orchestrator: "skills/ORCHESTRATOR.md"
```

**Required**: `instructions`
**Optional**: `permissions`, `orchestrator`

### Skills

```yaml
skills:
  - id: "discover"
    manifest: "skills/discover.skill.yaml"
    runbook: "skills/discover.md"
  - id: "train"
    manifest: "skills/train.skill.yaml"
    runbook: "skills/train.md"
```

Each skill has an `id` (unique within project), a `manifest` (structured YAML), and a `runbook` (Markdown).

### Registries

```yaml
registries:
  - id: "models"
    path: "registry/models.yaml"
    description: "ML models across 7 problem types"
  - id: "metrics"
    path: "registry/metrics.yaml"
    description: "Evaluation metrics and quality gates"
```

### Workflows

```yaml
workflows:
  - id: "dataset_pipeline"
    path: "workflows/pipeline.yaml"
  - id: "experiment_lifecycle"
    path: "workflows/experiment.yaml"
```

### Commands

```yaml
commands:
  - id: "train"
    path: "commands/train.md"
    trigger: "/train"
    description: "End-to-end model training with iteration"
```

### Dependencies

```yaml
dependencies:
  skills:
    "aes-hub/docker-deploy": "^1.2.0"
    "github:user/repo/.agent/skills/deploy": "v1.0.0"
```

Skills can be imported from a registry (`aes-hub/name@version`) or from git (`github:user/repo/path@ref`).

### Environment

```yaml
environment:
  required:
    - name: "API_KEY"
      description: "Main API key"
  optional:
    - name: "TIMEOUT"
      default: "300"
      description: "Operation timeout in seconds"
```

### Resources

```yaml
resources:
  max_cpu_percent: 70
  max_memory_percent: 75
  max_concurrent_jobs: 2
  coexistence_note: "Crypto bot has priority"
```

## Complete Example

```yaml
aes: "1.0"

name: "ml-model-factory"
version: "2.1.0"
description: "Automated ML pipeline: discover, train, evaluate, serve"
domain: "machine-learning"
license: "MIT"

author:
  name: "Hiro"

runtime:
  language: "python"
  version: "3.9"
  entry_point: "scripts/run_pipeline.py"
  setup: "setup.sh"

agent:
  instructions: "instructions.md"
  permissions: "permissions.yaml"
  orchestrator: "skills/ORCHESTRATOR.md"

skills:
  - id: "discover"
    manifest: "skills/discover.skill.yaml"
    runbook: "skills/discover.md"
  - id: "train"
    manifest: "skills/train.skill.yaml"
    runbook: "skills/train.md"

registries:
  - id: "models"
    path: "registry/models.yaml"

workflows:
  - id: "dataset_pipeline"
    path: "workflows/pipeline.yaml"

commands:
  - id: "train"
    path: "commands/train.md"
    trigger: "/train"

environment:
  required:
    - name: "OPENML_APIKEY"
      description: "OpenML API key"
  optional:
    - name: "OPTUNA_TIMEOUT"
      default: "300"

resources:
  max_cpu_percent: 70
  max_memory_percent: 75
```

## Validation

```bash
aes validate          # validates agent.yaml + all referenced files
```

The manifest is validated against `schemas/agent.schema.json`. All referenced paths (skills, registries, workflows, commands) are checked for existence.
