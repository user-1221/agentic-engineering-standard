# Continuous Learning

## Purpose

Extract, validate, evolve, and publish learned patterns (instincts) from agent sessions. Transforms ad-hoc experience into structured, confidence-scored knowledge that persists across sessions and can be shared via the AES registry.

## When to Use

- At the end of significant work sessions
- When the user explicitly requests `/learn`
- When a pattern has been applied multiple times in a session
- When correcting a previous mistake reveals a reusable lesson

## Four-Stage Pipeline

### Stage 1: Extraction

Triggered by the `extract-instincts` lifecycle hook at session end.

1. Review session actions for repeated patterns
2. Identify corrections (mistake → fix = learning opportunity)
3. Check for explicit `/learn` markers from the user
4. Create candidate instincts with `status: candidate`, `score: 0.4`
5. Save to `.agent/learning/instincts/candidates/`
6. Cap at `max_candidates_per_session` (default: 3) to prevent flooding

### Stage 2: Validation

Triggered by the `restore-context` lifecycle hook at session start.

1. Load active instincts into context (sorted by confidence, capped by token budget)
2. During the session, track instinct application:
   - Applied successfully → `validations++`, score increases
   - Overridden or produced bad outcome → `contradictions++`, score decreases
   - Partially applied (modified before use) → refine description and action
3. Update instinct files at session end

### Stage 3: Evolution

Runs periodically or on `aes validate`:

| Transition | Condition | Action |
|---|---|---|
| candidate → active | score >= `promotion_threshold` AND validations >= `promotion_min_validations` | Move to `active/` |
| active → refined | Partial application detected | Update description and action in place |
| active → archived | score < `min_score` | Move to `archived/` |
| Two instincts merged | High semantic overlap | Combine into one, merge evidence |

### Stage 4: Publishing

For high-confidence instincts:

1. Check eligibility: `score >= publish_threshold` AND `validations >= publish_min_validations`
2. Package as registry artifact: `aes publish --instinct <id> --registry`
3. Others install via: `aes install aes-hub/instinct-<id>@1.0`

## Instinct Format

Each instinct is a `.instinct.yaml` file with:
- **metadata**: id, timestamps, source session, tags
- **pattern**: description, trigger, action, evidence, examples
- **confidence**: score (0-1), validations count, contradictions count, status

## Configuration

Edit `.agent/learning/config.yaml` to tune:
- `extraction.max_candidates_per_session` — prevent flooding
- `confidence.promotion_threshold` — score needed to become active (default: 0.6)
- `context_loading.token_budget` — max tokens for instinct context (default: 2000)
- `context_loading.format` — `compact` (description + action) or `full` (includes evidence)

## Error Handling

- **Extraction fails**: Log warning, session continues normally
- **Instinct file corrupted**: Skip and warn during validation
- **Token budget exceeded**: Load highest-confidence instincts first, truncate rest
