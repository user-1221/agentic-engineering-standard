# Deep Research

## Purpose

Research-first development pattern. Before writing any code, thoroughly research existing solutions, evaluate trade-offs, and document findings. Prevents the common failure mode where agents reinvent existing solutions or choose suboptimal approaches without considering alternatives.

## When to Use

- Before implementing a new feature or system
- When choosing between multiple technical approaches
- When integrating with unfamiliar APIs or libraries
- When the user asks "what's the best way to..."
- Before any architectural decision

## Do NOT Use When

- Making a trivial change (typo fix, config update)
- The user explicitly says "just do it" or "skip research"
- Following up on a previously researched decision

## How It Works

### Phase 1: Define the Question

1. Restate the problem in your own words
2. Identify what "success" looks like (acceptance criteria)
3. List constraints (language, framework, performance, compatibility)
4. Identify what you already know vs. what needs research

### Phase 2: Search Existing Solutions

1. Search the current codebase for related implementations
2. Search documentation for relevant patterns or utilities
3. Search for existing libraries or packages that solve this
4. Check if the project's dependencies already provide the capability
5. Look for prior art in similar projects

### Phase 3: Evaluate Options

For each candidate solution, assess:

| Criterion | What to Check |
|---|---|
| Fit | Does it solve the actual problem? |
| Complexity | How much code/config is needed? |
| Maintenance | Is it actively maintained? Dependencies? |
| Performance | Does it meet performance requirements? |
| Compatibility | Does it work with existing stack? |
| Risk | What could go wrong? Rollback plan? |

### Phase 4: Document Decision

Create a brief decision record:
- **Context**: What prompted this decision
- **Options considered**: Each option with pros/cons
- **Decision**: Which option and why
- **Consequences**: What this means for the project

### Phase 5: Implement

Only now write code. The research phase should make implementation straightforward because:
- You know which approach to take
- You know which libraries to use
- You know the edge cases to handle
- You have a rollback plan

## Decision Tree

```
New feature or technical decision?
  ├── Trivial change? → Skip research, implement directly
  ├── Already researched? → Reference prior decision, implement
  └── Needs research? → Run full 5-phase pipeline
       ├── Found existing solution in codebase? → Reuse it
       ├── Found library that solves it? → Evaluate fit
       └── Novel problem? → Design from first principles, document thoroughly
```

## Error Handling

- **Research inconclusive**: Present findings to user, ask for direction
- **No good options**: Document why, propose custom solution with trade-offs
- **Time pressure**: Compress to 5-minute research, note areas needing deeper review
