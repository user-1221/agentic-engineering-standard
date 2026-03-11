# Skill: Analyze Content

## Purpose

Classify topics, extract key findings, and compute relevance scores. Identifies connections between items for later cross-referencing.

## When to Run

- Items at `parsed` status need analysis
- After parse stage completes for a batch

## How It Works

1. Load parsed content and metadata
2. Match against topic taxonomy using keyword and semantic similarity
3. Extract key findings from abstract, results, and conclusion sections
4. Compute relevance score based on topic match, recency, and citation count
5. Identify potential connections to existing analyzed items
6. Store analysis results and advance status to `analyzed`

## Decision Tree

```
For each parsed item:
  ├── No topics matched? → Assign "uncategorized", score = 0.1
  ├── Relevance score < 0.2? → Mark for rejection at organize stage
  ├── Key findings empty? → Extract from abstract only, flag as low-confidence
  ├── Similar items found? → Record connection candidates
  └── Analysis complete? → Advance to "analyzed"
```

## Error Handling

- **Topic taxonomy missing**: Use fallback keyword matching
- **Empty sections**: Score based on available content only
- **Analysis timeout**: Store partial results, flag for re-analysis
