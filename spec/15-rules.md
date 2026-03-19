# 15 — Rules & Conventions

Rules are coding standards, workflow conventions, and project norms expressed as first-class agent configuration. Instead of scattering the same guidelines across platform-specific directories, rules are defined once in `.agent/rules/` and compiled to every sync target. Language-specific rule sets are auto-detected or explicitly selected, and `${variable}` placeholders allow per-project customization without forking the rule files themselves.

## Motivation

- **Single source of truth**: Define coding standards once, compile to Claude Code, OpenClaw, Cursor, Codex, Copilot, and Windsurf — no manual duplication across platform directories
- **Auto-detection**: File-pattern heuristics load the right language rules automatically (TypeScript when `tsconfig.json` exists, Python when `pyproject.toml` exists, etc.)
- **Override system**: Projects customize thresholds and values (`min_coverage`, `branch_pattern`) in `rules.yaml` without editing the rule Markdown files
- **Publishable**: Rule directories can be published as AES templates and installed via `aes init --from aes-hub/coding-standards@1.0`

## Location

`.agent/rules/` — all rule files and the rules manifest live here.

```
.agent/rules/
  rules.yaml              # Rules manifest and configuration
  common/                 # Always loaded (language-agnostic)
  typescript/             # Loaded when TypeScript/JavaScript detected
  python/                 # Loaded when Python detected
  golang/                 # Loaded when Go detected
  swift/                  # Loaded when Swift detected
  php/                    # Loaded when PHP detected
```

## Rules Manifest

`rules.yaml` declares which rule sets to load, how to detect project languages, and project-specific overrides for variable placeholders.

```yaml
# .agent/rules/rules.yaml
apiVersion: aes/v1
kind: RulesConfig

# ── Explicit Language Selection ──────────────────────────
# When set, overrides auto-detection. Only these language
# rule sets are loaded (in addition to common/).
languages:
  - typescript
  - python

# ── Auto-Detection Patterns ─────────────────────────────
# Used when `languages` is empty or omitted. aes sync scans
# the project root for these file patterns and loads matching
# language rule sets.
detection:
  typescript: ["*.ts", "*.tsx", "tsconfig.json", "package.json"]
  python: ["*.py", "pyproject.toml", "setup.py", "requirements.txt"]
  golang: ["*.go", "go.mod"]
  swift: ["*.swift", "Package.swift"]
  php: ["*.php", "composer.json"]

# ── Loading Behavior ────────────────────────────────────
loading:
  always: [common]        # Always load these rule sets

# ── Project-Specific Overrides ──────────────────────────
# Keys correspond to rule file names (without extension).
# Values are maps of variable names to project-specific values.
# These resolve ${variable} placeholders in rule Markdown files.
overrides:
  testing:
    min_coverage: 90
    max_test_duration: 10s
  git-workflow:
    branch_pattern: "feature/*"
    require_pr_review: true
  coding-style:
    max_line_length: 120
    indent: spaces-2
```

### Manifest Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `apiVersion` | string | Yes | Always `aes/v1` |
| `kind` | string | Yes | Always `RulesConfig` |
| `languages` | string[] | No | Explicit language selection; overrides auto-detection |
| `detection` | map[string, string[]] | No | Language name to file-pattern globs for auto-detection |
| `loading.always` | string[] | No | Rule sets loaded regardless of language (default: `[common]`) |
| `overrides` | map[string, map[string, any]] | No | Per-rule variable overrides keyed by rule file name |

## Rule File Format

Each rule is a Markdown file with optional YAML frontmatter. The frontmatter declares metadata and default values for `${variable}` placeholders used in the body.

```markdown
---
name: testing
scope: common
priority: high
overridable_fields:
  - min_coverage
  - max_test_duration
defaults:
  min_coverage: 80
  max_test_duration: 5s
---

# Testing Standards

## Requirements
- Minimum ${min_coverage}% code coverage on all new code
- All public functions must have unit tests
- Integration tests for API endpoints
- No test should take longer than ${max_test_duration}

## Patterns
- Use Arrange-Act-Assert structure
- One assertion per test (prefer focused tests)
- Mock external dependencies, never real APIs in unit tests

## Anti-patterns
- Never test implementation details
- Never use sleep/delay in tests
- Never share state between tests
```

### Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Rule identifier (matches the filename without extension) |
| `scope` | string | Yes | `common` or a language name (e.g., `typescript`, `python`) |
| `priority` | enum | No | `high`, `medium`, or `low` (default: `medium`) — advisory for agents |
| `overridable_fields` | string[] | No | Which `${variable}` names can be overridden in `rules.yaml` |
| `defaults` | map[string, any] | No | Default values for each overridable variable |

Rules without frontmatter are treated as static Markdown with `priority: medium` and no overridable fields.

## Auto-Detection

When `languages` is omitted or empty in `rules.yaml`, `aes sync` scans the project root for file patterns defined in the `detection` map. Any language whose patterns match at least one file is activated.

Detection runs at sync time, not at validation time. This means:

1. `aes validate` checks that referenced rule directories exist and rule files parse correctly, but does not evaluate detection patterns.
2. `aes sync` evaluates detection, resolves the active language set, and compiles rules to each target.
3. If both `languages` (explicit) and `detection` are present, `languages` wins — detection is ignored.

### Default Detection Patterns

If `detection` is omitted from `rules.yaml`, the following defaults apply:

| Language | Patterns |
|----------|----------|
| `typescript` | `*.ts`, `*.tsx`, `tsconfig.json`, `package.json` |
| `python` | `*.py`, `pyproject.toml`, `setup.py`, `requirements.txt` |
| `golang` | `*.go`, `go.mod` |
| `swift` | `*.swift`, `Package.swift` |
| `php` | `*.php`, `composer.json` |

Projects may extend this map with custom language entries (e.g., `rust: ["*.rs", "Cargo.toml"]`). Any key that has a corresponding subdirectory under `.agent/rules/` is valid.

## Override System

Overrides resolve `${variable}` placeholders in rule Markdown files at sync time. The resolution order is:

1. **`rules.yaml` overrides** — highest priority. Values set under `overrides.<rule-name>.<variable>`.
2. **Frontmatter defaults** — fallback. Values set under `defaults.<variable>` in the rule file's YAML frontmatter.
3. **Undefined** — if neither source provides a value, the placeholder is left as-is in the compiled output and a warning is emitted during sync.

### Example

Given this override in `rules.yaml`:

```yaml
overrides:
  testing:
    min_coverage: 90
```

And this frontmatter in `common/testing.md`:

```yaml
defaults:
  min_coverage: 80
  max_test_duration: 5s
```

The compiled output resolves `${min_coverage}` to `90` (override wins) and `${max_test_duration}` to `5s` (frontmatter default, no override).

## Variable Resolution

### Placeholder Syntax

Variables use the `${variable_name}` syntax. Variable names must be alphanumeric with underscores (matching `[a-zA-Z_][a-zA-Z0-9_]*`).

### Escaping

To include a literal `${...}` in the compiled output (e.g., for shell variable examples in a rule), escape it with a backslash:

```markdown
Use \${HOME} in your shell scripts.
```

This compiles to the literal text `${HOME}` — the backslash is consumed during resolution.

### Undefined Variables

When a placeholder has no value from overrides or frontmatter defaults:

- **`aes sync`** emits a warning: `rules: unresolved variable '${var}' in <file>` and leaves the placeholder text in the output.
- **`aes validate`** reports it as a warning (not an error) — rules with unresolved variables are still valid.

This is intentional: rule packs designed for distribution may include variables that are only meaningful when overridden by the consuming project.

## Directory Structure

```
.agent/rules/
  rules.yaml                 # Manifest: languages, detection, overrides
  common/                    # Language-agnostic rules (always loaded)
    coding-style.md
    git-workflow.md
    testing.md
    security.md
    performance.md
  typescript/                # TypeScript/JavaScript conventions
    frameworks.md
    patterns.md
    tools.md
  python/                    # Python conventions
    style.md
    testing.md
    packaging.md
  golang/                    # Go conventions
    idioms.md
    concurrency.md
  swift/                     # Swift conventions
    style.md
    swiftui.md
  php/                       # PHP conventions
    laravel.md
    testing.md
```

### Conventions

- The `common/` directory is always loaded. It contains rules that apply regardless of language (git workflow, security, performance).
- Language directories are loaded based on detection or explicit selection. Their rule files may reference concepts from `common/` but should be self-contained.
- Rule filenames are kebab-case and serve as the key for `overrides` in `rules.yaml`.
- Subdirectories beyond one level are not supported — rules are flat within each language directory.

## Compilation Targets

`aes sync` compiles `.agent/rules/` into platform-specific formats. Common rules and detected language rules are processed through variable resolution and written to the appropriate target location.

| Target | Output Location | Transform |
|--------|----------------|-----------|
| Claude Code | `.claude/rules/common/*.md` + `.claude/rules/<lang>/*.md` | Direct copy with variable resolution |
| OpenClaw | Common rules merged into `workspace/SOUL.md`; language rules merged into `workspace/AGENTS.md` | Markdown sections appended to workspace files |
| Cursor | `.cursor/rules/*.md` | Direct copy with variable resolution |
| Codex | Embedded as `## Conventions` section in `AGENTS.md` | All rules (common + language) merged inline |
| Copilot | Embedded inline in instructions | All rules merged into Copilot instruction format |
| Windsurf | `.windsurf/rules/*.md` or inline | Direct copy with variable resolution; falls back to inline for older Windsurf versions |

### Target Details

**Claude Code** preserves the directory structure. Common rules go to `.claude/rules/common/` and language rules go to `.claude/rules/<lang>/`. Claude Code loads all files under `.claude/rules/` automatically, so no index file is needed.

**OpenClaw** merges rules into existing workspace Markdown files. Common rules (coding style, security, git workflow) are behavioral norms and belong in `SOUL.md`. Language-specific rules are technical operating instructions and belong in `AGENTS.md`. Rules are appended as new `##` sections under a `# Rules & Conventions` heading.

**Cursor** flattens all rules into `.cursor/rules/`. File names are preserved but the directory hierarchy is collapsed (e.g., `common/testing.md` becomes `.cursor/rules/testing.md`, `python/style.md` becomes `.cursor/rules/python-style.md`). If a name collision occurs, the language prefix is prepended.

**Codex** has no native rules directory. All rules are concatenated under a `## Conventions` section in the project's `AGENTS.md` file. Each rule file becomes a `###` subsection. This is a lossy compilation — the full Markdown is preserved but the file-per-rule structure is lost.

**Copilot** embeds rules inline in the generated instructions file. Like Codex, all rules are merged into a single document. Each rule becomes a section within the Copilot instruction payload.

**Windsurf** supports a `.windsurf/rules/` directory in recent versions. When available, rules are copied there with variable resolution (same as Cursor). For older Windsurf versions without directory support, rules are merged inline into the instructions file.

## Validation Rules

`aes validate` checks the following when `.agent/rules/` is present:

| Rule | Severity | Description |
|------|----------|-------------|
| `rules.yaml` parses as valid YAML | Error | Manifest must be syntactically valid |
| `apiVersion` is `aes/v1` | Error | Must match the expected API version |
| `kind` is `RulesConfig` | Error | Must be the correct kind |
| Referenced language directories exist | Error | If `languages: [typescript]`, then `.agent/rules/typescript/` must exist |
| Rule Markdown files have valid frontmatter | Warning | Frontmatter must parse as YAML if present |
| `overridable_fields` match `defaults` keys | Warning | Every overridable field should have a default |
| Overrides reference existing rule files | Warning | `overrides.testing` should correspond to a `testing.md` in some rule directory |
| No unresolved `${variable}` placeholders | Warning | Variables without defaults or overrides |
| `common/` directory exists | Warning | Expected but not strictly required |
| Rule files do not exceed 50KB | Warning | Large rule files may exceed agent context budgets |

Rules validation is integrated into the standard `aes validate` pipeline. The rules directory is optional — projects without `.agent/rules/` still validate.

## Publishable Rule Packs

Rule directories can be packaged as AES templates and shared via the registry. A rule pack is a self-contained `.agent/rules/` directory with a `rules.yaml` manifest, ready to install into any project.

### Publishing

```bash
aes publish --template --registry
```

When publishing a project that contains `.agent/rules/`, the rules directory is included in the template tarball. The `rules.yaml` manifest, all rule Markdown files, and the directory structure are preserved.

### Installing

```bash
aes init --from aes-hub/coding-standards@1.0
```

This installs the rule pack's `.agent/rules/` directory into the current project. If the project already has rules, the installer merges:

- New language directories are added alongside existing ones
- Conflicting rule files prompt for resolution (keep existing, overwrite, or merge)
- `rules.yaml` overrides are preserved from the existing project — the installed pack's defaults do not overwrite project-specific values

### Example Registry Packages

| Package | Description |
|---------|-------------|
| `aes-hub/coding-standards@1.0` | Multi-language rule pack (TypeScript, Python, Go, Swift, PHP) with common conventions |
| `aes-hub/security-rules@1.0` | Security-focused rules: OWASP patterns, dependency scanning, secret detection |
| `aes-hub/team-conventions@1.0` | Team workflow rules: PR templates, commit conventions, review checklists |

## Relationship to Other Specs

- **[06-permissions.md](06-permissions.md)**: Permissions control what an agent *can* do (file access, network, shell). Rules define what an agent *should* do (coding standards, workflow norms). They are complementary — permissions are enforced, rules are advisory.
- **[02-instructions.md](02-instructions.md)**: Instructions are the agent's primary playbook. Rules are specific, granular conventions that supplement instructions. During sync, rules are compiled into platform-specific locations separate from the main instructions file.
- **[03-skills.md](03-skills.md)**: Skills may reference rules (e.g., a "code review" skill checks against coding-style rules), but skills and rules are independent artifacts with separate directories and manifests.
