# 09 — Sharing: Publishing, Versioning, and Dependencies

AES supports two sharing units: **skills** (individual capabilities) and **templates** (complete `.agent/` configurations). This document defines how both are packaged, versioned, published, discovered, and installed.

## Skill Package Format

A shareable skill is a directory containing:

```
my-skill/
  skill.yaml            # Manifest (required)
  runbook.md            # Agent runbook (required)
  README.md             # Human documentation (recommended)
  tests/                # Tests (recommended)
    test_skill.py
  examples/             # Usage examples (optional)
    basic.md
```

Minimum viable skill: `skill.yaml` + `runbook.md`.

## Template Package Format

A template is a complete `.agent/` directory packaged as a tarball — the full agentic configuration for a project type.

```
my-template-1.0.0.tar.gz
  my-template/
    .agent/
      agent.yaml            # Manifest (required)
      instructions.md       # Agent instructions
      permissions.yaml      # Permissions
      skills/               # All skills
      workflows/            # Workflows
      commands/             # Agent commands
      registry/             # Component registries
```

### Privacy Controls

`.agent/` directories may contain sensitive files. By default, template packages **exclude**:

- `memory/**` — Agent memory (session history, learned context)
- `local.yaml` — Local overrides (API keys, user-specific config)
- `overrides/**` — Tool-specific override files

These defaults can be overridden:

```bash
aes publish --template                           # default exclusions
aes publish --template --include-memory          # include memory/
aes publish --template --include-all             # no exclusions
aes publish --template --exclude "secrets/**"    # additional exclusions
```

### Publishing Templates

```bash
aes publish --template -o dist/ --path ./my-project
aes publish --template --registry --path ./my-project
```

This:
1. Validates the `.agent/` directory against schemas
2. Applies privacy exclusions
3. Packages as `{name}-{version}.tar.gz` with structure `{name}/.agent/...`
4. Optionally uploads to the registry with `type: "template"`

### Installing Templates

```bash
aes init --from aes-hub/ml-pipeline@^2.0         # from registry
aes init --from ./ml-pipeline-2.1.0.tar.gz       # from local tarball
```

This:
1. Resolves the version from the registry index
2. Downloads and verifies the tarball (SHA256)
3. Extracts the `.agent/` directory into the project root
4. Runs `aes sync` to generate tool-specific config files

### Registry Index Type Field

Package entries in `index.json` include a `type` field:

```json
{
  "packages": {
    "ml-pipeline": {
      "type": "template",
      "description": "Complete ML pipeline agent configuration",
      "latest": "2.1.0",
      "versions": { ... }
    },
    "deploy": {
      "type": "skill",
      "description": "Deploy skill",
      "latest": "1.0.0",
      "versions": { ... }
    }
  }
}
```

Valid values: `"skill"` (default) or `"template"`. Packages without a `type` field are treated as skills for backward compatibility.

### Registry Index Visibility Field

Package entries may include a `visibility` field:

```json
{
  "packages": {
    "internal-deploy": {
      "type": "skill",
      "visibility": "private",
      "description": "Internal deploy skill",
      "latest": "1.0.0",
      "versions": { ... }
    }
  }
}
```

Valid values: `"public"` (default) or `"private"`. Packages without a `visibility` field are treated as public for backward compatibility.

- **Public** packages appear in search results and can be downloaded by anyone.
- **Private** packages require a valid registry token (`AES_REGISTRY_KEY`) to appear in search results and to download.

### Searching by Type

```bash
aes search --type template              # list all templates
aes search --type skill                 # list all skills
aes search --type template --tag ml     # templates tagged "ml"
```

## Package Manifest

Every package tarball contains an `aes-manifest.json` at the root of the archive. Inspired by OCI image manifests, it provides a content-addressable inventory of every file in the package.

```json
{
  "schemaVersion": 1,
  "mediaType": "application/vnd.aes.package.v1+tar+gzip",
  "config": {
    "name": "ml-pipeline",
    "version": "2.1.0",
    "type": "template",
    "aes": "1.2"
  },
  "layers": [
    {
      "mediaType": "application/vnd.aes.agent-config.v1+yaml",
      "digest": "sha256:abc123...",
      "size": 1234,
      "path": ".agent/agent.yaml"
    },
    {
      "mediaType": "application/vnd.aes.agent-config.v1+yaml",
      "digest": "sha256:def456...",
      "size": 567,
      "path": ".agent/bom.yaml"
    }
  ],
  "signature": null
}
```

### Fields

| Field | Description |
|-------|-------------|
| `schemaVersion` | Always `1` for this version |
| `mediaType` | Package media type |
| `config.name` | Package name from agent.yaml |
| `config.version` | Package version from agent.yaml |
| `config.type` | `"skill"` or `"template"` |
| `config.aes` | AES spec version |
| `layers` | Array of file entries |
| `layers[].mediaType` | File media type (YAML, Markdown, etc.) |
| `layers[].digest` | SHA256 hash of file contents |
| `layers[].size` | File size in bytes |
| `layers[].path` | Path within the package |
| `signature` | Optional cryptographic signature (reserved for future use) |

### Verification

Tools can verify package integrity by:
1. Extracting `aes-manifest.json` from the tarball
2. For each layer, computing the SHA256 of the file and comparing to `digest`
3. If all digests match, the package is intact

### BOM Inclusion

When `bom.yaml` exists, it is automatically included as a layer in the manifest. This ensures the AI-BOM is always available for inspection without extracting the full package.

## Versioning

Skills follow [Semantic Versioning](https://semver.org/):

- **Major** (2.0.0): Breaking changes to inputs, outputs, or interface
- **Minor** (1.1.0): New optional inputs/outputs, new features
- **Patch** (1.0.1): Bug fixes, documentation updates

### What Counts as Breaking?

| Change | Breaking? |
|--------|-----------|
| Remove a required input | Yes (major) |
| Add a required input | Yes (major) |
| Change output format | Yes (major) |
| Add an optional input | No (minor) |
| Add a new output field | No (minor) |
| Fix a bug in the runbook | No (patch) |
| Update description | No (patch) |

## Dependencies

### Declaring Dependencies

In `agent.yaml`:

```yaml
dependencies:
  skills:
    # From the AES registry
    "aes-hub/docker-deploy": "^1.2.0"
    "aes-hub/github-pr-review": "~2.0.0"

    # From a Git repository
    "github:user/repo/.agent/skills/deploy": "v1.0.0"

    # From a local path (development)
    "local:../shared-skills/monitoring": "*"
```

### Version Ranges

| Syntax | Meaning |
|--------|---------|
| `"1.2.3"` | Exact version |
| `"^1.2.0"` | Compatible with 1.x.x (>=1.2.0, <2.0.0) |
| `"~1.2.0"` | Patch-level changes (>=1.2.0, <1.3.0) |
| `">=1.0.0"` | Minimum version |
| `"*"` | Any version (for local development) |

### Skill-to-Skill Dependencies

Skills can declare dependencies on other skills:

```yaml
# In train.skill.yaml
depends_on:
  - skill: "preprocess"
    version: ">=1.0.0"
  - skill: "evaluate"
    version: ">=1.0.0"
```

### Resolution

When `aes install` runs:
1. Read `agent.yaml` dependencies
2. Resolve version ranges to specific versions
3. Download skill packages
4. Place in `.agent/skills/vendor/` (vendored dependencies)
5. Update `.agent/skills/vendor.lock` (lockfile)

```
.agent/skills/
  vendor/                          # Installed dependencies
    aes-hub/
      docker-deploy/
        skill.yaml
        runbook.md
    github/
      user-repo/
        deploy/
          skill.yaml
          runbook.md
  vendor.lock                      # Lockfile (exact versions)
```

## Publishing

### To the AES Registry

```bash
aes publish ./skills/train --registry
```

This:
1. Validates the skill manifest against the schema
2. Packages the skill directory as `.tar.gz`
3. Uploads the tarball to the registry (requires `AES_REGISTRY_KEY`)
4. Updates the registry `index.json` with the new version and SHA256 hash

By default packages are public. To publish a private package:

```bash
aes publish --skill train --registry --visibility private
```

When `--visibility` is omitted in interactive mode, the CLI prompts for selection.

The registry is a static file store (S3/R2-compatible):
```
registry/
  index.json                          # skill catalog
  packages/
    deploy/
      1.0.0.tar.gz
      1.1.0.tar.gz
```

Environment variables:
- `AES_REGISTRY_URL` — override default registry URL (default: `https://registry.aes-official.com`)
- `AES_REGISTRY_KEY` — auth token for publish (bearer token)

### As a Git Repository

The simplest sharing method — no registry needed:

1. Put skills in your repo under `.agent/skills/`
2. Tag releases with semver (`v1.0.0`)
3. Others reference via git URL in their `agent.yaml`

```yaml
dependencies:
  skills:
    "github:hiro/ml-factory/.agent/skills/train": "v2.1.0"
```

### As a Tarball

For manual sharing:

```bash
aes publish ./skills/train          # creates train-1.0.0.tar.gz
```

## Discovery

### Search

```bash
aes search "ml training"            # search registry by keywords
aes search --domain ml              # filter by domain
aes search --tag "data-ingestion"   # filter by tag
aes search                          # list all packages
```

The `aes search` command fetches the registry `index.json`, filters packages by keyword, tag, or domain, and displays a table of results with name, latest version, description, and tags.

### Inspect

`aes inspect` also works with remote registry packages:

```bash
aes inspect deploy                      # inspect latest version
aes inspect aes-hub/deploy@^1.0.0      # inspect specific version range
aes inspect deploy@1.0.0               # inspect exact version
```

Shows registry metadata (all versions, published dates, tags) plus package contents: for skill packages, the full manifest (inputs, outputs, dependencies, triggers); for template packages, the same project overview as local inspect.

## Composability

Skills compose naturally through the workflow system:

1. **Sequential**: Skill A's output status is Skill B's input status
2. **Parallel**: Skills with no dependencies can run concurrently
3. **Conditional**: Workflow transitions have conditions

The orchestrator coordinates this — individual skills don't need to know about each other.

## Namespace Convention

| Source | Format | Example |
|--------|--------|---------|
| AES Registry | `aes-hub/{name}` | `aes-hub/docker-deploy` |
| GitHub | `github:{user}/{repo}/{path}` | `github:hiro/factory/.agent/skills/train` |
| Local | `local:{path}` | `local:../shared/monitoring` |

## Compatibility

Skills declare which AES version they require:

```yaml
aes_skill: "1.0"    # requires AES 1.0 or compatible
```

Tools that implement AES 1.x can use any skill with `aes_skill: "1.0"`.
