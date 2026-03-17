# Command: /memory

Review the current conversation and save memory-worthy items to `.agent/memory/`.

## When to Run

- **Manually**: Run `/memory` at any point to persist important learnings
- **Auto-trigger**: Run this at the end of significant work sessions — after completing commands, making architectural decisions, solving difficult bugs, or finishing substantial implementation work

## Phase 1: Review Context

Scan the conversation and identify items worth persisting:

1. **Architectural decisions** — new patterns, technology choices, design trade-offs with rationale
2. **Hard-won solutions** — bugs that took effort to diagnose, non-obvious fixes, workarounds
3. **Project conventions** — patterns confirmed across multiple interactions
4. **Environment/infra notes** — deployment details, runtime quirks, credentials setup
5. **Status changes** — what was built, what shifted to in-progress or planned

**Ignore:**
- Temporary state (current task details, in-progress work details)
- Single-observation conclusions not yet confirmed across sessions
- Information already captured in `.agent/instructions.md`
- Session-specific details (temp file paths, ephemeral IDs)

## Phase 2: Check Existing Memory

Read the current memory files to avoid duplicates:

1. `.agent/memory/project.md` — check all sections
2. `.agent/memory/learnings.yaml` — check existing learning IDs

For each candidate item:
- **Updates** an existing entry → modify the existing entry in place
- **Contradicts** an existing entry → replace with the newer understanding
- **Genuinely new** → append to the appropriate section
- **Duplicates** an existing entry → skip

## Phase 3: Save to Project Memory

Update `.agent/memory/project.md` with items that belong in these sections:

| Section | What goes here |
|---------|---------------|
| **Project Overview** | System purpose changes, scope shifts |
| **Architecture** | New technical decisions with rationale |
| **Status** | What's built, in progress, planned |
| **Key Patterns** | Confirmed patterns from the codebase |
| **Environment Notes** | Deployment, runtime, infrastructure details |

Keep `project.md` under 200 lines. If approaching the limit, consolidate or remove outdated entries rather than exceeding it.

## Phase 4: Save Structured Learnings

For hard-won lessons with clear applicability, append to `.agent/memory/learnings.yaml`:

```yaml
- id: "kebab-case-id"
  date: "YYYY-MM-DD"
  context: "what was happening"
  observation: "what was observed"
  lesson: "generalized takeaway"
  applies_when:
    - "condition 1"
    - "condition 2"
  action: "what to do when this applies"
```

Only create structured learnings for insights that:
- Were confirmed across multiple observations, OR
- Required significant effort to discover, OR
- Would cause real damage if forgotten

## Phase 5: Session Snapshot

If the session involved substantial work, create `.agent/memory/sessions/YYYY-MM-DD.md`:

```markdown
# Session: YYYY-MM-DD

## What Was Done
- ...

## Decisions Made
- ...

## Open Questions
- ...
```

Skip this phase for minor sessions (quick fixes, small config changes).

## Phase 6: Report

Summarize what was persisted:
- Items added or updated in `project.md`
- Learnings added to `learnings.yaml` (if any)
- Session file created (if any)
- Items skipped as duplicates
