# Evaluation Harness

## Purpose

Systematic verification loops for agent work. Defines two evaluation modes, multiple grader types, and pass@k sampling for robust quality assurance. Ensures agent output meets defined quality bars before marking work as complete.

## When to Use

- After completing a feature or fix
- Before merging or deploying code
- When the user requests "verify this works"
- During autonomous operation to validate each step

## Evaluation Modes

### Checkpoint Mode

Evaluate at predefined gates in the workflow:

1. **After implementation**: Does the code compile? Do imports resolve?
2. **After tests written**: Do all tests pass? Coverage above threshold?
3. **After integration**: Does the system work end-to-end?
4. **Before deploy**: Security scan clean? Performance acceptable?

Use when: work follows a defined pipeline with clear stages.

### Continuous Mode

Evaluate after every change:

1. Run the relevant test subset after each file edit
2. Check type correctness after each function change
3. Validate API contracts after each endpoint change
4. Run linter after each commit

Use when: making many small changes, or when early failure detection saves time.

## Grader Types

### Assertion-Based

Automated checks with clear pass/fail:

```
- Does the function return the expected type?
- Does the API respond with 200 for valid input?
- Does the test suite pass?
- Is code coverage above the threshold?
```

Best for: objective, measurable criteria.

### LLM-as-Judge

Use a language model to evaluate subjective quality:

```
- Is this error message helpful and actionable?
- Does this documentation explain the concept clearly?
- Is this code idiomatic for the language?
- Does this API design follow REST conventions?
```

Best for: subjective quality, readability, design decisions.
Provider-agnostic: works with any model that accepts a grading prompt.

### Human-in-Loop

Request human verification for high-stakes decisions:

```
- Does this migration look correct before running on prod?
- Is this the right architectural approach?
- Should we proceed with this breaking change?
```

Best for: irreversible actions, architectural decisions, production changes.

## Pass@k Sampling

For non-deterministic tasks, sample multiple solutions:

1. Generate k candidate solutions (e.g., k=3)
2. Run evaluation on each
3. Select the best-scoring candidate
4. Report pass@k metric (what fraction passed)

Use when: the task has multiple valid approaches and you want the best one.

## How to Set Up

1. Define evaluation criteria for your workflow stages
2. Choose grader type per criterion (assertion, LLM, human)
3. Set thresholds (e.g., "all assertions pass", "LLM score >= 4/5")
4. Configure mode (checkpoint gates or continuous)
5. Run evaluations and iterate

## Error Handling

- **Assertion fails**: Report which check failed, suggest fix
- **LLM grader disagrees with assertions**: Flag for human review
- **All k samples fail**: Report common failure pattern, ask for guidance
- **Evaluation timeout**: Skip with warning, note unevaluated items
