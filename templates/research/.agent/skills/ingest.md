# Skill: Ingest Content

## Purpose

Collect papers, articles, and content from configured sources. Deduplicates by DOI, URL, and title similarity.

## When to Run

- No items in `ingested` status
- User requests new sources to be ingested
- Scheduled periodic run

## How It Works

1. Query each configured source adapter (arXiv, Semantic Scholar, RSS, web)
2. For each candidate item, check deduplication criteria (DOI, URL, title similarity)
3. Download raw content and store in `data/raw/`
4. Insert record with provenance metadata (source, access date, URL)
5. Set status to `ingested`

## Decision Tree

```
For each candidate item:
  ├── DOI already exists? → Skip
  ├── URL already exists? → Skip
  ├── Title similarity > 0.9 to existing? → Skip
  ├── Content unreachable? → Log warning, skip
  └── Passes all checks? → Insert as "ingested"
```

## Error Handling

- **API timeout**: Retry once with exponential backoff, then skip source
- **Rate limit**: Sleep per source-specific backoff, then retry
- **Download failure**: Log error, skip item, continue with next
