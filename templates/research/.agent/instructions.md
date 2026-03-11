# Research Pipeline — Agent Instructions

Research content processing pipeline. Ingests papers and articles, extracts structure and metadata, analyzes findings, organizes by topic taxonomy, and generates reports.

## Quick Reference

```bash
python scripts/pipeline.py --stage all
python scripts/pipeline.py --stage ingest --source arxiv
python scripts/pipeline.py --stage analyze --item-id 42
python scripts/pipeline.py status
```

## Project Structure

```
pipeline/          # ingest, parse, analyze, organize, display
config/            # settings, topic_taxonomy, sources
data/              # raw content, parsed output, knowledge graph
output/            # reports, summaries, dashboards
scripts/           # CLI entry points
```

## Critical Rules

1. **Source attribution** — always record provenance and access date.
2. **Deduplication** — check by identifier, URL, title similarity before inserting.
3. **Relevance filtering** — reject items below configured threshold.
4. **Incremental processing** — resume from last completed stage, never re-process.
5. **Structured output** — all results in structured format (JSON, YAML, or typed objects).
6. **Fail graceful** — each item wrapped in try/except, log error, continue pipeline.

## Primary Workflow

### Phase 1: Ingest Sources
Query configured sources (arXiv, Semantic Scholar, RSS, web). Deduplicate by DOI, URL, and title similarity.

### Phase 2: Extract Structure
Parse into sections, metadata, and citations. Supports PDF, HTML, plain text.

### Phase 3: Analyze & Classify
Topic classification, finding extraction, relevance scoring. Items below threshold are rejected.

### Phase 4: Organize & Connect
Build taxonomy, cross-reference related items, update knowledge graph.

### Phase 5: Generate Output
Produce reports, summaries, and dashboards in markdown, HTML, or JSON format.

## Key Principle

Content is the raw material; structured knowledge is the product. Every item flows through the pipeline from raw ingestion to organized, cross-referenced output.

## Common Gotchas

- PDF parsing may fail on scanned documents — fall back to OCR or skip.
- arXiv rate limits are strict (3 req/sec) — use exponential backoff.
- Relevance scores are relative to the configured topic taxonomy — update taxonomy before re-scoring.
- Knowledge graph connections are additive — removing an item does not remove its cross-references.
