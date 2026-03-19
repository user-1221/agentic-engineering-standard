# AES v2: ECC-Derived Additions

**Lifecycle Hooks, Continuous Learning, Rules System, Skills Extraction**

Technical specification for features inspired by everything-claude-code (81K★)

March 2026

---

## 1. What ECC Has That AES Doesn't

Everything Claude Code (affaan-m/everything-claude-code) is an 81K-star Claude Code plugin providing battle-tested agents, skills, hooks, commands, rules, and MCP configurations. After analyzing its full codebase, three systems stand out as genuinely novel patterns that AES should adopt as platform-agnostic specs, plus several concrete skills worth publishing to the AES registry.

| ECC Feature | What It Does | AES Equivalent Today | Action |
|---|---|---|---|
| hooks.json lifecycle system | Session start/end, pre/post tool use hooks with profiles and async support | Nothing — no lifecycle spec exists | New spec: spec/11-lifecycle.md |
| continuous-learning-v2 | Auto-extract patterns from sessions into instincts with confidence scoring and evolution | memory/ spec is primitive — no structured learning | New spec: spec/12-learning.md |
| rules/ directory | common/ + language-specific coding standards with layered overrides | permissions.yaml covers security only, not conventions | New spec: spec/13-rules.md |
| Specialized agents (planner, architect, TDD, reviewer) | Pre-built sub-agent definitions with delegation chains | AES has no agent definition examples for dev workflows | Publish as template to registry |
| deep-research, eval-harness, autonomous-loops skills | Portable development methodology skills | AES registry has no community skills yet | Convert and publish to registry |
| .claude/ + .cursor/ + .codex/ + .opencode/ manual sync | Same configs maintained separately per platform | aes sync only targets Claude/Cursor | Add ECC as import source |

*The fundamental difference: ECC maintains platform-specific copies manually. AES defines once and compiles to each platform. Every feature below is designed as a format spec that aes sync consumes.*

---

## 2. New Spec: Lifecycle Hooks (spec/11-lifecycle.md)

### 2.1 What ECC Does Today

ECC uses a hooks/hooks.json file that registers scripts on Claude Code lifecycle events. Key features:

- **SessionStart hook** — Restores previous session context (summary + memory) so the agent doesn't start cold
- **Stop hook** — Persists session summary at termination (moved to Stop phase because transcript payload only exists there)
- **PreToolUse hook** — Quality gates that validate tool calls before execution (e.g., block dangerous rm commands)
- **PostToolUse hook** — Logging, metrics collection after tool execution
- **ECC_HOOK_PROFILE** — Runtime flag (minimal|standard|strict) that controls which hooks are active without editing config
- **ECC_DISABLED_HOOKS** — Comma-separated list of specific hooks to disable at runtime
- **async: true** — Hooks can run in background without blocking the agent (added in v1.8.0)
- **Script-based hooks** — All hooks rewritten from fragile inline one-liners to dedicated Node.js scripts for cross-platform reliability

**Problem:** This only works for Claude Code. Cursor, OpenClaw, Codex, and OpenCode each have completely different lifecycle event systems. ECC has no way to make these hooks portable.

### 2.2 AES Lifecycle Spec Design

A new file .agent/lifecycle.yaml declares hooks in a platform-agnostic format. The aes sync pipeline compiles these declarations into the correct format for each target platform.

#### 2.2.1 Complete Schema

```yaml
# .agent/lifecycle.yaml
apiVersion: aes/v1
kind: Lifecycle

# ─── Runtime profile (controls which hooks are active) ───
profile: standard                  # minimal | standard | strict

# ─── Disabled hooks (override without editing this file) ───
# Also controllable via AES_DISABLED_HOOKS env var
disabled_hooks: []

# ─── Hook definitions ───
hooks:

  # ════════════════════════════════════════════════════
  # SESSION LIFECYCLE
  # ════════════════════════════════════════════════════

  on_session_start:
    - name: restore-context
      description: >
        Load previous session summary, active instincts,
        and persistent memory into agent context.
      profile: minimal              # Available in all profiles
      action: script
      command: node .agent/scripts/restore-context.js
      timeout_seconds: 10
      async: false                  # Block until context is loaded
      fail_strategy: warn           # warn | skip | abort
      inputs:                       # Data passed to script
        - memory_dir: .agent/memory/
        - learning_dir: .agent/learning/instincts/active/
        - sessions_dir: .agent/learning/sessions/

  on_session_end:
    - name: persist-summary
      description: >
        Save a compressed summary of this session for
        the next session's restore-context hook.
      profile: minimal
      action: script
      command: node .agent/scripts/persist-summary.js
      timeout_seconds: 15
      async: true                   # Don't block session exit
      fail_strategy: warn

    - name: extract-instincts
      description: >
        Review session actions and extract candidate
        instincts for the learning system.
      profile: standard             # Not in minimal profile
      action: script
      command: node .agent/scripts/extract-instincts.js
      timeout_seconds: 30
      async: true
      fail_strategy: skip

  # ════════════════════════════════════════════════════
  # TOOL LIFECYCLE
  # ════════════════════════════════════════════════════

  pre_tool_use:
    - name: quality-gate
      description: >
        Validate tool calls against project rules.
        Blocks dangerous operations in strict mode.
      profile: strict               # Only in strict profile
      action: script
      command: node .agent/scripts/quality-gate.js
      filter:
        tools: [Edit, Write, Bash, Execute]
      timeout_seconds: 5
      async: false                  # Must complete before tool runs
      fail_strategy: abort          # Block the tool call on failure

    - name: doc-warning
      description: >
        Warn before modifying documentation files
        unless explicitly instructed.
      profile: standard
      action: script
      command: node .agent/scripts/doc-warning.js
      filter:
        tools: [Edit, Write]
        paths: ["*.md", "docs/**"]
      timeout_seconds: 3
      async: false
      fail_strategy: warn

  post_tool_use:
    - name: audit-log
      description: >
        Log tool name, input, output, duration,
        and result status for audit trail.
      profile: standard
      action: script
      command: node .agent/scripts/audit-log.js
      async: true
      fail_strategy: skip
      output:
        file: .agent/logs/audit.jsonl
        format: jsonl

  # ════════════════════════════════════════════════════
  # PERIODIC
  # ════════════════════════════════════════════════════

  heartbeat:
    interval_minutes: 30
    actions:
      - name: check-tasks
        description: Review pending tasks and act proactively
        action: checklist
        checklist_file: .agent/heartbeat.md

      - name: compact-check
        description: >
          Check accumulated context size and suggest
          compaction if above threshold.
        action: script
        command: node .agent/scripts/compact-check.js
        config:
          threshold_tokens: 100000

  # ════════════════════════════════════════════════════
  # ERROR HANDLING
  # ════════════════════════════════════════════════════

  on_error:
    - name: error-recovery
      description: >
        Attempt graceful recovery: save state,
        log error context, retry if transient.
      action: script
      command: node .agent/scripts/error-recovery.js
      max_retries: 3
      backoff_seconds: 5
      fail_strategy: warn
```

#### 2.2.2 Profile System

Profiles control which hooks are active at runtime. Each hook declares the minimum profile it requires:

| Profile | Active Hooks | Use Case |
|---|---|---|
| minimal | Only hooks with profile: minimal (session start/end) | Debugging, low-overhead sessions, quick tasks |
| standard | minimal + hooks with profile: standard (audit, doc-warning, instinct extraction) | Normal development work |
| strict | standard + hooks with profile: strict (quality gates with abort-on-fail) | Production code, regulated environments, CI/CD |

Override at runtime via environment variable: `AES_HOOK_PROFILE=minimal`. Disable specific hooks: `AES_DISABLED_HOOKS=audit-log,compact-check`.

#### 2.2.3 Hook Fields Reference

| Field | Type | Required | Description |
|---|---|---|---|
| name | string | Yes | Unique identifier for this hook |
| description | string | Yes | What this hook does (shown in aes inspect) |
| profile | enum | No (default: standard) | Minimum profile to activate: minimal \| standard \| strict |
| action | enum | Yes | Execution type: script \| checklist |
| command | string | If action=script | Shell command to execute (prefer node for cross-platform) |
| checklist_file | string | If action=checklist | Markdown file with checklist items |
| filter.tools | string[] | No | Only trigger for these tool types |
| filter.paths | string[] | No | Only trigger for files matching these globs |
| timeout_seconds | integer | No (default: 30) | Max execution time before kill |
| async | boolean | No (default: false) | Run in background without blocking agent |
| fail_strategy | enum | No (default: warn) | On failure: warn (log + continue) \| skip (silent) \| abort (block action) |
| inputs | object | No | Data paths passed to the script as environment/args |
| output.file | string | No | Where the hook writes its output |
| output.format | string | No | Output format: jsonl \| json \| md |
| max_retries | integer | No | For on_error hooks only: retry count |
| backoff_seconds | integer | No | For on_error hooks only: delay between retries |

#### 2.2.4 Compilation Targets

aes sync compiles lifecycle.yaml into platform-specific hook configurations:

**Claude Code → hooks/hooks.json**

```json
// Generated by: aes sync --target claude-code
{
  "hooks": [
    {
      "type": "command",
      "event": "SessionStart",
      "command": "node .agent/scripts/restore-context.js",
      "timeout": 10
    },
    {
      "type": "command",
      "event": "Stop",
      "command": "node .agent/scripts/persist-summary.js",
      "async": true,
      "timeout": 15
    },
    {
      "type": "command",
      "event": "PreToolUse",
      "command": "node .agent/scripts/quality-gate.js",
      "timeout": 5,
      "toolNames": ["Edit", "Write", "Bash", "Execute"]
    },
    {
      "type": "command",
      "event": "PostToolUse",
      "command": "node .agent/scripts/audit-log.js",
      "async": true
    }
  ]
}
```

**OpenClaw → Multiple outputs**

| AES Hook Type | OpenClaw Output | How It Works |
|---|---|---|
| on_session_start | Gateway startup event handler | Registered in openclaw.json as gateway plugin |
| on_session_end | Gateway shutdown event handler | Runs on SIGTERM/SIGINT |
| heartbeat | workspace/HEARTBEAT.md | OpenClaw's built-in heartbeat scheduler reads this file |
| pre/post_tool_use | Gateway middleware | Intercepts tool calls in the agent runtime loop |
| on_error | Gateway error handler | Registered as error middleware |

**Cursor → .cursor/hooks/ directory**

Cursor supports limited hook-like behavior through automation rules. Only pre_tool_use and post_tool_use map cleanly. Session hooks are compiled as .cursor/rules/ entries that instruct the agent to run scripts at appropriate moments.

**Codex → AGENTS.md sections**

Codex has no native hook system. Hooks are compiled as behavioral instructions embedded in AGENTS.md, telling the agent to execute scripts at lifecycle boundaries. This is a lossy compilation — enforcement depends on model compliance rather than runtime enforcement.

### 2.3 New Directory Structure

```
.agent/
  lifecycle.yaml               # Hook declarations (this spec)
  scripts/                     # Hook implementation scripts
    restore-context.js
    persist-summary.js
    extract-instincts.js
    quality-gate.js
    doc-warning.js
    audit-log.js
    compact-check.js
    error-recovery.js
  heartbeat.md                 # Heartbeat checklist
  logs/                        # Hook output directory
    audit.jsonl                # Audit trail (generated by hooks)
```

### 2.4 JSON Schema Addition

Add `lifecycle.schema.json` to schemas/ directory. Key validation rules:

- Each hook name must be unique within its event type
- `profile` must be one of: minimal, standard, strict
- `fail_strategy` must be one of: warn, skip, abort
- `action: checklist` requires `checklist_file`; `action: script` requires `command`
- `filter.tools` and `filter.paths` only valid on pre_tool_use and post_tool_use hooks
- `max_retries` and `backoff_seconds` only valid on on_error hooks

---

## 3. New Spec: Continuous Learning (spec/12-learning.md)

### 3.1 What ECC Does Today

ECC's continuous-learning-v2 skill implements an instinct-based learning system:

- **Instincts** — Learned patterns extracted from sessions with YAML frontmatter (Action, Evidence, Examples sections)
- **Confidence scoring** — Each instinct has a numerical confidence that increases with validation and decreases with time
- **Import/export** — Instincts can be shared between projects via /instinct-import and /instinct-export commands
- **Session integration** — Active instincts are injected into context at session start

**Problem:** ECC's instinct format is Claude Code-specific Markdown. There's no structured schema, no validation, no cross-platform portability, and no standard way to publish instincts to a shared registry. The parse_instinct_file() function had a bug (silently dropping content after frontmatter) that went undetected because there was no schema enforcement.

### 3.2 AES Learning Spec Design

The learning system defines a structured format for instincts, a four-stage pipeline for their lifecycle, and integration with the AES registry for sharing.

#### 3.2.1 Instinct Format

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

#### 3.2.2 Instinct Fields Reference

| Field | Type | Required | Description |
|---|---|---|---|
| metadata.id | string | Yes | Unique identifier (kebab-case) |
| metadata.created_at | datetime | Yes | When the instinct was first extracted |
| metadata.last_validated | datetime | Yes | When the instinct was last confirmed in a session |
| metadata.source_session | string | Yes | Session ID that generated this instinct |
| metadata.tags | string[] | No | Searchable tags for categorization |
| pattern.description | string | Yes | What the pattern is (the core learning) |
| pattern.trigger | string | Yes | When this instinct should activate |
| pattern.action | string | Yes | Step-by-step instructions to follow |
| pattern.evidence[] | array | No | Session outcomes that validate this instinct |
| pattern.examples[] | array | No | Concrete applications with context |
| confidence.score | float | Yes | 0.0 to 1.0 confidence level |
| confidence.validations | int | Yes | Number of positive confirmations |
| confidence.contradictions | int | Yes | Number of times overridden |
| confidence.decay_rate | float | No | Score decrease per week without validation (default: 0.01) |
| confidence.min_score | float | No | Below this score, instinct is archived (default: 0.3) |
| confidence.status | enum | Yes | candidate \| active \| archived |

#### 3.2.3 Learning Pipeline (Four Stages)

**Stage 1: Extraction** — Triggered by the `extract-instincts` hook at session end (see lifecycle spec). The script reviews the session transcript and identifies patterns that were:

- Applied more than once in the session
- Used to correct a previous mistake
- Explicitly marked as a learning by the user (/learn command) or agent

New instincts are created with `status: candidate` and `score: 0.4` in the `candidates/` directory.

**Stage 2: Validation** — Triggered by the `restore-context` hook at session start. Active instincts are loaded into the agent's context (up to `max_instincts_in_context` and `token_budget` limits). During the session:

- If an instinct is applied and the outcome is positive: `validations++`, score increases
- If an instinct is overridden or produces a negative outcome: `contradictions++`, score decreases
- If an instinct is partially applied (modified before use): the description and action fields are refined

**Stage 3: Evolution** — Runs periodically (or on `aes validate`):

| Transition | Condition | What Happens |
|---|---|---|
| Candidate → Active | score >= promotion_threshold AND validations >= promotion_min_validations | Moved from candidates/ to active/ directory |
| Active → Refined | Partial application detected (modified before use) | description and action fields updated in place |
| Active → Archived | score < min_score (due to decay or contradictions) | Moved from active/ to archived/ directory |
| Two instincts → Merged | High semantic overlap detected between two active instincts | Combined into single instinct, evidence and examples merged |

**Stage 4: Publishing** — High-confidence instincts can be shared:

- Instincts with `score >= publish_threshold` (default 0.8) and `validations >= publish_min_validations` (default 5) are eligible
- `aes publish --instinct api-error-handling --registry` packages the instinct as a registry artifact
- `aes install aes-hub/instinct-api-error-handling@1.0` installs it into another project's learning directory

#### 3.2.4 Learning Configuration

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

#### 3.2.5 Directory Structure

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

#### 3.2.6 Compilation Targets

Active instincts are injected into platform-specific context files during aes sync:

| Platform | Where Instincts Go | Format |
|---|---|---|
| Claude Code | Injected into CLAUDE.md via SessionStart hook | Markdown section: ## Learned Patterns |
| OpenClaw | Appended to workspace/AGENTS.md | Markdown section merged with operating instructions |
| Cursor | Written to .cursor/rules/instincts.md | Rule file loaded as project convention |
| Codex | Appended to AGENTS.md | Instruction section |
| Any (fallback) | Appended to .agent/instructions.md | Markdown section at end of playbook |

### 3.3 Key Differences from ECC

- **Structured YAML vs freeform Markdown** — ECC instincts are Markdown with frontmatter that can silently lose content on parse errors. AES instincts are validated YAML with a JSON schema
- **Publishable** — ECC instincts live in a single project. AES instincts with high confidence can be published to the registry and installed by other projects
- **Platform-portable** — ECC instincts only load in Claude Code. AES instincts compile to any sync target
- **Configurable token budget** — ECC loads all instincts. AES respects token_budget and max_instincts_in_context to prevent context window bloat

---

## 4. New Spec: Rules & Conventions (spec/13-rules.md)

### 4.1 What ECC Does Today

ECC has a rules/ directory with this structure:

```
rules/
  common/               # Language-agnostic (always install)
    coding-style.md
    git-workflow.md
    testing.md
    performance.md
    patterns.md
    hooks.md
    agents.md
    security.md
  typescript/            # TS/JS specific
  python/                # Python specific
  golang/                # Go specific
  swift/                 # Swift specific
  php/                   # PHP specific
```

These are installed via a shell script that copies rule files into ~/.claude/rules/ (global) or .claude/rules/ (project). Language-specific rules reference their common/ counterparts. The same rules are then manually duplicated into .cursor/rules/, .codex/, and .opencode/ directories.

**Problem:** Manual duplication. When a rule changes, it must be updated in 4+ platform directories separately. There's no auto-detection of which language rules to load, no override system, and no validation.

### 4.2 AES Rules Spec Design

#### 4.2.1 Directory Structure

```
.agent/
  rules/
    rules.yaml                   # Rules manifest and configuration
    common/                      # Always loaded
      coding-style.md
      git-workflow.md
      testing.md
      security.md
      performance.md
    typescript/                   # Loaded when TS/JS detected
      frameworks.md
      patterns.md
      tools.md
    python/                      # Loaded when Python detected
      style.md
      testing.md
      packaging.md
    golang/
    swift/
    php/
```

#### 4.2.2 Rules Manifest: rules.yaml

```yaml
apiVersion: aes/v1
kind: RulesConfig

# Explicit language selection (overrides auto-detection)
languages:
  - typescript
  - python

# Auto-detection patterns (used when languages is empty)
detection:
  typescript: ["*.ts", "*.tsx", "tsconfig.json", "package.json"]
  python: ["*.py", "pyproject.toml", "setup.py", "requirements.txt"]
  golang: ["*.go", "go.mod"]
  swift: ["*.swift", "Package.swift"]
  php: ["*.php", "composer.json"]

loading:
  always: [common]                # Always load these rule sets
  # Language-specific sets loaded based on detection or explicit list

# Override specific rule values per project
overrides:
  testing:
    min_coverage: 90              # Override default 80% threshold
  git-workflow:
    branch_pattern: "feature/*"   # Override branch naming
    require_pr_review: true
  coding-style:
    max_line_length: 120
    indent: spaces-2
```

#### 4.2.3 Rule File Format

Each rule is a Markdown file with optional YAML frontmatter for metadata:

```markdown
---
name: testing
scope: common
priority: high                  # high | medium | low
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

The `${variable}` placeholders are resolved from rules.yaml overrides at sync time, allowing project-specific customization without modifying the rule files themselves.

#### 4.2.4 Compilation Targets

| Platform | Output | Transform |
|---|---|---|
| Claude Code | .claude/rules/common/*.md + .claude/rules/\<lang\>/*.md | Direct copy with variable resolution |
| OpenClaw | Merged into workspace/SOUL.md (behavioral) and workspace/AGENTS.md (technical) | Common rules → SOUL.md; language rules → AGENTS.md |
| Cursor | .cursor/rules/*.md | Direct copy with variable resolution |
| Codex | .codex/AGENTS.md sections | Embedded as instruction sections |
| OpenCode | .opencode/rules/*.md | Direct copy with variable resolution |

### 4.3 Key Differences from ECC

- **Single source of truth** — Rules defined once in .agent/rules/, compiled to all platforms. ECC maintains 4+ separate copies
- **Auto-detection** — AES detects project languages from file patterns and loads the right rule sets. ECC requires manual installation via shell script
- **Override system** — Projects can override specific values (coverage threshold, branch pattern) in rules.yaml without forking rule files. ECC has no override mechanism
- **Variable resolution** — Rule templates use ${var} placeholders resolved at sync time. ECC rules are static Markdown
- **Publishable rule packs** — Rule directories can be published as AES templates and installed via `aes init --from aes-hub/coding-standards@1.0`

---

## 5. Skills to Extract & Publish from ECC

These skills should be converted from ECC format into AES skill.yaml + runbook.md pairs and published to registry.aes-official.com. They serve two purposes: populating the registry with useful content, and demonstrating that AES skills carry the same value as ECC skills but in a portable format.

### 5.1 Tier 1: Individual Skills (Publish Immediately)

#### continuous-learning

Implements the instinct extraction and evolution system from Section 3. This is the flagship skill — it demonstrates a capability no other standard offers and directly uses the new learning spec.

- **ECC source:** skills/continuous-learning-v2/
- **AES package:** `aes-hub/continuous-learning@1.0.0`
- **Includes:** skill.yaml, runbook.md, plus .agent/scripts/ for the extraction and validation hooks
- **Dependencies:** Requires spec/11-lifecycle.md and spec/12-learning.md to be implemented

#### deep-research

Research-first development pattern. Before writing any code, the agent researches existing solutions, evaluates trade-offs, documents findings, and only then implements. Prevents the common failure mode where agents reinvent existing solutions.

- **ECC source:** skills/deep-research/
- **AES package:** `aes-hub/deep-research@1.0.0`
- **Key adaptation:** Remove Claude Code-specific tool references. Make the research steps tool-agnostic (works with any web search, documentation lookup, or code search capability)

#### eval-harness

Verification loops with two evaluation modes (checkpoint: evaluate at defined gates; continuous: evaluate after every change), multiple grader types (LLM-as-judge, assertion-based, human-in-loop), and pass@k metrics for sampling multiple solutions.

- **ECC source:** skills/eval-harness/
- **AES package:** `aes-hub/eval-harness@1.0.0`
- **Key adaptation:** Generalize grader configs to work with any model provider, not just Anthropic API

#### autonomous-loops

Patterns for long-running autonomous agent sessions: loop detection (identifying when the agent is stuck repeating actions), progress tracking (measurable checkpoints), graceful termination (clean shutdown with state preservation), and checkpoint recovery (resume from last known good state).

- **ECC source:** skills/autonomous-loops/
- **AES package:** `aes-hub/autonomous-loops@1.0.0`
- **Key adaptation:** Essential for OpenClaw always-on agents. Frame the runbook around 24/7 operation rather than development sessions

### 5.2 Tier 2: Template Packs (Publish as Templates)

#### coding-standards-template

Converts ECC's language-specific rules into an AES rules/ overlay that installs into any project's .agent/rules/ directory.

- **ECC sources:** rules/common/ + rules/typescript/ + rules/python/ + rules/golang/ + rules/swift/ + rules/php/
- **AES package:** `aes-hub/coding-standards@1.0.0` (template)
- **Install:** `aes init --from aes-hub/coding-standards@1.0`
- **Includes:** rules.yaml with defaults and override documentation, plus all rule Markdown files

#### dev-workflow-template

Converts ECC's agent delegation chain into an AES workflow with state machine definition. Shows how a development task flows through specialized sub-agents: planner → architect → TDD guide → implementer → code reviewer → security reviewer.

- **ECC sources:** agents/ directory (planner.md, architect.md, tdd-guide.md, code-reviewer.md, security-reviewer.md, build-error-resolver.md, e2e-runner.md, refactor-cleaner.md, doc-updater.md)
- **AES package:** `aes-hub/dev-workflow@1.0.0` (template)
- **Install:** `aes init --from aes-hub/dev-workflow@1.0`
- **Includes:** AES workflow YAML defining the state machine, plus skill definitions for each agent role

---

## 6. Implementation Priority

Ordered by dependency chain and strategic value:

### Phase 1: Foundation (Week 1–2)

| Item | Effort | Depends On | Deliverable |
|---|---|---|---|
| spec/13-rules.md | 2 days | Nothing | Rules directory spec + rules.schema.json + sync for Claude/Cursor/OpenClaw |
| spec/11-lifecycle.md | 3 days | Nothing | Lifecycle hooks spec + lifecycle.schema.json + Claude Code hooks.json compilation |
| lifecycle.schema.json | 0.5 days | spec/11-lifecycle.md | JSON schema for validation |
| rules.schema.json | 0.5 days | spec/13-rules.md | JSON schema for validation |

### Phase 2: Learning System (Week 2–3)

| Item | Effort | Depends On | Deliverable |
|---|---|---|---|
| spec/12-learning.md | 4 days | spec/11-lifecycle.md (hooks trigger extraction) | Learning spec + instinct.schema.json + config schema |
| Extract instincts scripts | 2 days | spec/12-learning.md | Node.js scripts for .agent/scripts/ (extraction, validation, decay) |
| instinct.schema.json | 0.5 days | spec/12-learning.md | JSON schema for instinct files |

### Phase 3: Registry Population (Week 3–4)

| Item | Effort | Depends On | Deliverable |
|---|---|---|---|
| Publish continuous-learning skill | 1.5 days | spec/12-learning.md | aes-hub/continuous-learning@1.0.0 on registry |
| Publish deep-research skill | 1 day | Nothing | aes-hub/deep-research@1.0.0 on registry |
| Publish eval-harness skill | 1 day | Nothing | aes-hub/eval-harness@1.0.0 on registry |
| Publish autonomous-loops skill | 1 day | Nothing | aes-hub/autonomous-loops@1.0.0 on registry |
| Publish coding-standards template | 1.5 days | spec/13-rules.md | aes-hub/coding-standards@1.0.0 on registry |
| Publish dev-workflow template | 2 days | Nothing | aes-hub/dev-workflow@1.0.0 on registry |

### Phase 4: Adoption (Week 4–5)

| Item | Effort | Depends On | Deliverable |
|---|---|---|---|
| Import test suite | 1 day | All three new specs | Regression tests against real ECC repo structure |
| Community post / announcement | 0.5 days | Registry packages published | Announce on ECC Discussions and relevant channels |

---

*End of document. Three new spec documents (lifecycle, learning, rules). Six registry packages (4 skills + 2 templates). Zero modifications to existing AES specs — these are purely additive.*
