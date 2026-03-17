# 11 — Agent Bill of Materials (AI-BOM)

An Agent Bill of Materials tracks every component an agent depends on: AI models, ML frameworks, tools, and data sources. Like an SBOM for software, the AI-BOM gives compliance, security, and operations teams a single document that answers "what is this agent made of?"

## Motivation

- **Compliance**: EU AI Act (August 2026) requires transparency about AI components
- **Security**: Know which models and tools have access to your data
- **Reproducibility**: Pin exact versions of every component
- **Audit**: Trace decisions back to the model and data that produced them

## Location

`.agent/bom.yaml` — always at this path, always this filename.

## Format

YAML with comments. Validated against `schemas/bom.schema.json`.

```yaml
aes_bom: "1.2"

models:
  - name: "claude-sonnet-4-20250514"
    provider: "anthropic"
    license: "proprietary"
    purpose: "primary"
    hash: "sha256:..."              # optional, for pinning

frameworks:
  - name: "catboost"
    version: "1.2.2"
    license: "Apache-2.0"

tools:
  - name: "fetch"
    type: "mcp-server"             # mcp-server | cli | api
    version: "1.0.0"
    source: "npm:@anthropic/mcp-fetch"

data_sources:
  - name: "openml"
    type: "api"                    # api | file | database
    uri: "https://www.openml.org/api/v1"
    license: "CC-BY-4.0"
```

## Sections

### Models

AI models the agent uses. Each entry declares:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Model identifier (e.g., `claude-sonnet-4-20250514`) |
| `provider` | Yes | Who provides the model (`anthropic`, `openai`, etc.) |
| `license` | No | License type (`proprietary`, `Apache-2.0`, etc.) |
| `purpose` | No | How the model is used: `primary`, `fallback`, `embedding`, `evaluation` |
| `hash` | No | SHA256 hash for pinning a specific model artifact |

### Frameworks

ML/AI frameworks and libraries the agent relies on.

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Framework name |
| `version` | No | Pinned version |
| `license` | No | License identifier |

### Tools

External tools the agent invokes (MCP servers, CLIs, APIs).

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Tool name |
| `type` | Yes | `mcp-server`, `cli`, or `api` |
| `version` | No | Tool version |
| `source` | No | Where to obtain the tool |

### Data Sources

Data the agent reads from or writes to.

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Data source name |
| `type` | Yes | `api`, `file`, or `database` |
| `uri` | No | Location or endpoint |
| `license` | No | Data license |

## CLI

```bash
aes bom                    # display BOM for current project
aes bom ./path/to/project  # display BOM for specific project
```

The `aes bom` command reads `.agent/bom.yaml` and displays a summary table.

## Relationship to agent.yaml

`agent.yaml` has a `models` section that declares which models the agent uses. `bom.yaml` is the full inventory — it includes everything from `agent.yaml` plus frameworks, tools, and data sources. The two files complement each other:

- **agent.yaml `models`**: What models the agent *is configured to use* (runtime config)
- **bom.yaml**: What the agent *is made of* (full component inventory)

## Packaging

When `aes publish --template` packages a project, `bom.yaml` is automatically included in the tarball. The package manifest (`aes-manifest.json`) references it explicitly.

## Validation

```bash
aes validate          # validates bom.yaml if present
```

`bom.yaml` is validated against `schemas/bom.schema.json`. It is optional — projects without a BOM still validate.
