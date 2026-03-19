# 14 — Continuous Learning

Continuous Learning defines a structured system for extracting, validating, evolving, and sharing learned patterns (instincts) across agent sessions. Instead of ad-hoc memory accumulation, the learning system uses confidence-scored instincts that are promoted, refined, or archived based on real-world outcomes — turning session experience into durable, portable knowledge.

## Motivation

- **Structured over ad-hoc**: Raw memory files grow without bound and lack quality signals. Instincts have confidence scores, validation counts, and decay rates — the system self-prunes
- **Pattern extraction**: Instincts are extracted from session transcripts automatically, capturing patterns the agent applied repeatedly or used to correct mistakes
- **Confidence scoring**: Every instinct carries a 0.0–1.0 confidence score that increases with positive validation and decreases with contradictions or time-based decay
- **Cross-session continuity**: Active instincts are injected into the agent context at session start, so learned patterns persist without manual curation
- **Publishable knowledge**: High-confidence instincts can be packaged and shared through the AES registry, letting teams and the community benefit from proven patterns

## Location

`.agent/learning/` — all learning system files live here. Configuration, instinct files, and session logs are organized into subdirectories by lifecycle stage.

## Instinct Format

Each instinct is a standalone YAML file validated against `schemas/instinct.schema.json`.

```yaml
# .agent/learning/instincts/active/api-error-handling.instinct.yaml
apiVersion: aes/v1
kind: Instinct

metadata:
  id: api-error-handling
  created_at: "2026-03-15T10:30:00Z"
  last_validated: "2026-03-19T14:00:00Z"
  source_session: session-2026-03-15-abc123
  tags: [error-handling, api, resilience]

pattern:
  description: >
    When making external API calls, always implement retry
    with exponential backoff and circuit breaker pattern
    for transient failures.

  trigger: >
    Agent is implementing or modifying code that makes
    external HTTP/API calls.

  action: |
    1. Wrap call in try/catch with typed error handling
    2. Implement 3-retry exponential backoff (1s, 2s, 4s)
    3. Add circuit breaker (opens after 5 consecutive failures)
    4. Log each attempt with structured metadata
    5. Return meaningful error to caller on final failure

  evidence:
    - session: session-2026-03-15-abc123
      outcome: "Reduced API timeout errors by 90%"
    - session: session-2026-03-17-def456
      outcome: "Validated in production load test"
    - session: session-2026-03-19-ghi789
      outcome: "Caught 3 transient failures during deploy"

  examples:
    - context: Building REST client for payment gateway
      application: >
        Applied retry + circuit breaker to all payment API calls.
        Caught 3 transient 503 errors that would have caused
        transaction failures.
    - context: Refactoring notification service
      application: >
        Added circuit breaker to SMS provider. When provider
        went down, requests failed fast instead of queueing.

confidence:
  score: 0.85
  validations: 4
  contradictions: 0
  decay_rate: 0.01
  min_score: 0.3
  status: active                 # candidate | active | archived
```

## Instinct Fields Reference

### Metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metadata.id` | string | Yes | Unique identifier (kebab-case) |
| `metadata.created_at` | datetime | Yes | When the instinct was first extracted |
| `metadata.last_validated` | datetime | Yes | When the instinct was last confirmed in a session |
| `metadata.source_session` | string | Yes | Session ID that generated this instinct |
| `metadata.tags` | string[] | No | Searchable tags for categorization |

### Pattern

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern.description` | string | Yes | What the pattern is (the core learning) |
| `pattern.trigger` | string | Yes | When this instinct should activate |
| `pattern.action` | string | Yes | Step-by-step instructions to follow |
| `pattern.evidence[]` | array | No | Session outcomes that validate this instinct |
| `pattern.evidence[].session` | string | Yes (per entry) | Session ID where the instinct was validated |
| `pattern.evidence[].outcome` | string | Yes (per entry) | Description of the observed outcome |
| `pattern.examples[]` | array | No | Concrete applications with context |
| `pattern.examples[].context` | string | Yes (per entry) | Situation where the instinct was applied |
| `pattern.examples[].application` | string | Yes (per entry) | How the instinct was applied and what happened |

### Confidence

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `confidence.score` | float | Yes | 0.0 to 1.0 confidence level |
| `confidence.validations` | int | Yes | Number of positive confirmations |
| `confidence.contradictions` | int | Yes | Number of times overridden or contradicted |
| `confidence.decay_rate` | float | No | Score decrease per week without validation (default: `0.01`) |
| `confidence.min_score` | float | No | Below this score, instinct is archived (default: `0.3`) |
| `confidence.status` | enum | Yes | `candidate`, `active`, or `archived` |

## Learning Configuration

`.agent/learning/config.yaml` controls extraction behavior, confidence thresholds, and context loading limits.

```yaml
# .agent/learning/config.yaml
apiVersion: aes/v1
kind: LearningConfig

extraction:
  enabled: true
  auto_extract: true               # Auto-extract at session end
  min_session_length: 5            # Min turns before extraction triggers
  max_candidates_per_session: 3    # Prevent instinct flooding

confidence:
  initial_score: 0.4               # Starting score for new candidates
  promotion_threshold: 0.6         # Score needed to become active
  promotion_min_validations: 3     # Min validations to promote
  publish_threshold: 0.8           # Score needed to publish
  publish_min_validations: 5       # Min validations to publish
  decay_rate_per_week: 0.01        # Score decrease without validation
  min_score: 0.3                   # Below this, archive the instinct

context_loading:
  max_instincts_in_context: 10     # Token budget management
  sort_by: confidence_score        # Load highest confidence first
  token_budget: 2000               # Max tokens for instinct context
  format: compact                  # compact | full
  # compact: only description + action (saves tokens)
  # full: description + action + evidence + examples
```

### Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `extraction.enabled` | bool | `true` | Whether the learning system is active |
| `extraction.auto_extract` | bool | `true` | Automatically extract instincts at session end |
| `extraction.min_session_length` | int | `5` | Minimum conversation turns before extraction |
| `extraction.max_candidates_per_session` | int | `3` | Cap on new instincts per session |
| `confidence.initial_score` | float | `0.4` | Starting confidence for new candidates |
| `confidence.promotion_threshold` | float | `0.6` | Score required to promote candidate to active |
| `confidence.promotion_min_validations` | int | `3` | Minimum validations before promotion |
| `confidence.publish_threshold` | float | `0.8` | Score required for registry publishing |
| `confidence.publish_min_validations` | int | `5` | Minimum validations before publishing |
| `confidence.decay_rate_per_week` | float | `0.01` | Weekly score reduction without validation |
| `confidence.min_score` | float | `0.3` | Archive threshold |
| `context_loading.max_instincts_in_context` | int | `10` | Maximum instincts loaded per session |
| `context_loading.sort_by` | string | `confidence_score` | Sort order for loading priority |
| `context_loading.token_budget` | int | `2000` | Maximum tokens allocated to instinct context |
| `context_loading.format` | enum | `compact` | `compact` (description + action only) or `full` (all fields) |

## Four-Stage Pipeline

The learning system operates as a four-stage pipeline. Instincts flow through extraction, validation, evolution, and optionally publishing.

### Stage 1: Extraction

Triggered by the `extract-instincts` lifecycle hook at session end (see [13-lifecycle.md](13-lifecycle.md)). The extraction script reviews the session transcript and identifies patterns that were:

- Applied more than once in the session
- Used to correct a previous mistake
- Explicitly marked as a learning by the user (`/learn` command) or agent

New instincts are created with `status: candidate` and `score: 0.4` (the `initial_score` from config) in the `candidates/` directory.

### Stage 2: Validation

Triggered by the `restore-context` lifecycle hook at session start. Active instincts are loaded into the agent's context, subject to `max_instincts_in_context` and `token_budget` limits. During the session:

- If an instinct is applied and the outcome is positive: `validations` increments, score increases
- If an instinct is overridden or produces a negative outcome: `contradictions` increments, score decreases
- If an instinct is partially applied (modified before use): the `description` and `action` fields are refined

### Stage 3: Evolution

Runs periodically or when `aes validate` is invoked. The evolution stage manages instinct lifecycle transitions:

| Transition | Condition | What Happens |
|------------|-----------|--------------|
| Candidate &rarr; Active | `score >= promotion_threshold` AND `validations >= promotion_min_validations` | Moved from `candidates/` to `active/` directory |
| Active &rarr; Refined | Partial application detected (modified before use) | `description` and `action` fields updated in place |
| Active &rarr; Archived | `score < min_score` (due to decay or contradictions) | Moved from `active/` to `archived/` directory |
| Two instincts &rarr; Merged | High semantic overlap detected between two active instincts | Combined into single instinct; evidence and examples merged |

### Stage 4: Publishing

High-confidence instincts can be shared through the AES registry:

- Instincts with `score >= publish_threshold` (default `0.8`) and `validations >= publish_min_validations` (default `5`) are eligible
- `aes publish --instinct <id> --registry` packages the instinct as a registry artifact
- `aes install aes-hub/instinct-<id>@1.0` installs it into another project's learning directory

Published instincts are installed with `status: active` and their original confidence metadata preserved. The receiving project's validation cycle then applies local evidence.

## Directory Structure

```
.agent/
  learning/
    config.yaml                    # Learning system configuration
    instincts/
      active/                      # Currently loaded into sessions
        api-error-handling.instinct.yaml
        test-first-development.instinct.yaml
        structured-logging.instinct.yaml
      candidates/                  # Extracted but not yet promoted
        new-pattern-001.instinct.yaml
      archived/                    # Below min_score, preserved for reference
        deprecated-pattern.instinct.yaml
    sessions/                      # Per-session learning logs
      2026-03-19.learning.jsonl    # What was applied, validated, contradicted
```

### Directory Purposes

| Directory | Contents | Lifecycle |
|-----------|----------|-----------|
| `active/` | Instincts loaded into agent context at session start | Promoted from candidates, or installed from registry |
| `candidates/` | Newly extracted instincts awaiting validation | Created by extraction, promoted or archived by evolution |
| `archived/` | Instincts that fell below `min_score` | Preserved for reference; can be manually restored |
| `sessions/` | JSONL logs of per-session learning activity | One file per session; records applications, validations, contradictions |

### Session Log Format

Each line in a `.learning.jsonl` file is a JSON object:

```json
{"timestamp": "2026-03-19T14:32:00Z", "instinct_id": "api-error-handling", "event": "applied", "outcome": "positive", "context": "Added retry logic to payment client"}
{"timestamp": "2026-03-19T15:10:00Z", "instinct_id": "test-first-development", "event": "contradicted", "outcome": "negative", "context": "Skipped TDD for quick hotfix — user explicitly requested implementation first"}
```

## Compilation Targets

Active instincts are injected into platform-specific context files during `aes sync`. Each target receives instincts in the format its platform expects.

### Claude Code

Injected into `CLAUDE.md` via the `SessionStart` lifecycle hook as a `## Learned Patterns` section. Each active instinct is rendered as a subsection with its trigger and action.

```markdown
## Learned Patterns

### api-error-handling (confidence: 0.85)
**When:** Agent is implementing or modifying code that makes external HTTP/API calls.
**Do:**
1. Wrap call in try/catch with typed error handling
2. Implement 3-retry exponential backoff (1s, 2s, 4s)
3. Add circuit breaker (opens after 5 consecutive failures)
...
```

### OpenClaw

Appended to `workspace/AGENTS.md` as a dedicated section. Instincts are merged with the existing operating instructions so the agent encounters them as part of its standard workspace context.

### Cursor

Written to `.cursor/rules/instincts.md` as a rule file. Cursor loads project rules from this directory automatically, so instincts become part of the project convention set.

### Codex

Appended to `AGENTS.md` as a `## Learned Patterns` section. Codex has no native instinct system — enforcement depends on model compliance rather than runtime mechanisms. This is a lossy compilation.

### Copilot

Appended to the Copilot instructions file. Instincts are rendered as behavioral guidelines that Copilot incorporates into its code generation context.

### Any (fallback)

For platforms without a dedicated sync target, instincts are appended to `.agent/instructions.md` as a `## Learned Patterns` section at the end of the playbook. This ensures instincts are available regardless of which tool consumes the instructions file.

### Compilation Summary

| Platform | Output Location | Format | Fidelity |
|----------|----------------|--------|----------|
| Claude Code | `CLAUDE.md` (via SessionStart hook) | `## Learned Patterns` section | Full — hook-based injection |
| OpenClaw | `workspace/AGENTS.md` | Merged with operating instructions | Full — native workspace integration |
| Cursor | `.cursor/rules/instincts.md` | Rule file | Full — loaded as project rules |
| Codex | `AGENTS.md` | `## Learned Patterns` section | Lossy — model compliance only |
| Copilot | Instructions file | Appended guidelines | Lossy — model compliance only |
| Any (fallback) | `.agent/instructions.md` | `## Learned Patterns` section | Full — generic Markdown |

## Registry Publishing

Instincts that meet the publishing threshold become first-class registry packages, shareable across projects and teams.

### Eligibility

An instinct is eligible for publishing when:

- `confidence.score >= publish_threshold` (default `0.8`)
- `confidence.validations >= publish_min_validations` (default `5`)

### Publishing Workflow

```bash
# Publish a single instinct
aes publish --instinct api-error-handling --registry

# Install a published instinct
aes install aes-hub/instinct-api-error-handling@1.0
```

The publish command packages the instinct YAML along with its evidence and examples into a registry artifact. The package manifest includes:

- The instinct file itself
- Original confidence metadata (score, validations, contradictions)
- Source project information (anonymized unless `--include-source` is specified)
- Tags for registry search and discovery

Installed instincts are placed in the receiving project's `active/` directory with their original metadata. The local validation cycle then applies project-specific evidence, allowing the confidence score to evolve independently from the source.

## Relationship to Lifecycle

The learning system depends on lifecycle hooks (see [13-lifecycle.md](13-lifecycle.md)) for its two automated triggers:

### extract-instincts Hook

Registered as an `on_session_end` hook. After a session completes, this hook reviews the session transcript and creates candidate instincts in `candidates/`. The hook respects `extraction.min_session_length` and `extraction.max_candidates_per_session` from the learning config.

```yaml
# In .agent/lifecycle.yaml
on_session_end:
  - name: extract-instincts
    description: >
      Review session actions and extract candidate
      instincts for the learning system.
    profile: standard
    action: script
    command: node .agent/scripts/extract-instincts.js
    timeout_seconds: 30
    async: true
    fail_strategy: skip
```

### restore-context Hook

Registered as an `on_session_start` hook. At the beginning of each session, this hook loads active instincts into the agent's context window, subject to `context_loading` limits.

```yaml
# In .agent/lifecycle.yaml
on_session_start:
  - name: restore-context
    description: >
      Load previous session summary, active instincts,
      and persistent memory into agent context.
    profile: minimal
    action: script
    command: node .agent/scripts/restore-context.js
    timeout_seconds: 10
    async: false
    fail_strategy: warn
    inputs:
      - learning_dir: .agent/learning/instincts/active/
```

### Manual Operation

The learning system can also operate without lifecycle hooks. Projects that do not use `lifecycle.yaml` can manage instincts manually:

- Run extraction scripts directly: `node .agent/scripts/extract-instincts.js`
- Create instinct files by hand following the schema
- Use `aes validate` to trigger the evolution stage

## Validation Rules

Instinct files are validated against `schemas/instinct.schema.json`. The schema enforces:

### Required Structure

- `apiVersion` must be `aes/v1`
- `kind` must be `Instinct`
- `metadata.id` must be a non-empty string in kebab-case
- `metadata.created_at` and `metadata.last_validated` must be valid ISO 8601 datetimes
- `metadata.source_session` must be a non-empty string
- `pattern.description`, `pattern.trigger`, and `pattern.action` must be non-empty strings
- `confidence.score` must be a number between 0.0 and 1.0
- `confidence.validations` and `confidence.contradictions` must be non-negative integers
- `confidence.status` must be one of: `candidate`, `active`, `archived`

### Consistency Checks

- An instinct in `active/` must have `confidence.status: active`
- An instinct in `candidates/` must have `confidence.status: candidate`
- An instinct in `archived/` must have `confidence.status: archived`
- `confidence.score` must be consistent with `confidence.min_score` — an active instinct with `score < min_score` produces a warning

### Config Validation

`config.yaml` is validated against `schemas/learning-config.schema.json`:

- `confidence.initial_score` must be between 0.0 and 1.0
- `confidence.promotion_threshold` must be greater than `confidence.initial_score`
- `confidence.publish_threshold` must be greater than `confidence.promotion_threshold`
- `confidence.min_score` must be less than `confidence.initial_score`
- `context_loading.format` must be one of: `compact`, `full`

### CLI

```bash
aes validate          # validates instinct files and config if present
```

The learning directory is optional — projects without `.agent/learning/` still validate. When present, all `.instinct.yaml` files and `config.yaml` are validated against their respective schemas.
