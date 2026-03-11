# Skill: Organize Content

## Purpose

Categorize analyzed items into the topic taxonomy, build cross-references, and update the knowledge graph. Turns isolated analyses into connected knowledge.

## When to Run

- Items at `analyzed` status with relevance_score >= 0.2
- After analyze stage completes for a batch

## How It Works

1. Load analysis results (topics, findings, relevance score)
2. Map topics to taxonomy categories (may create new subcategories)
3. Find related items by topic overlap, citation links, and finding similarity
4. Create bidirectional cross-references in knowledge graph
5. Update category indices and statistics
6. Advance status to `organized`

## Decision Tree

```
For each analyzed item:
  ├── relevance_score < 0.2? → Mark rejected
  ├── No taxonomy category match? → Create "emerging" subcategory
  ├── Cross-references found? → Record bidirectional links
  ├── Duplicate of existing organized item? → Merge, keep richer version
  └── Organization complete? → Advance to "organized"
```

## Error Handling

- **Knowledge graph locked**: Retry after brief delay
- **Category conflict**: Log warning, assign to most specific matching category
- **Missing cross-reference target**: Skip link, log for later reconciliation
