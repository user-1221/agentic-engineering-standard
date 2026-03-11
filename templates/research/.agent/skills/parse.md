# Skill: Parse Content

## Purpose

Extract structure, metadata, key sections, and citations from raw content. Converts unstructured documents into a normalized representation.

## When to Run

- Items at `ingested` status need processing
- After new content has been ingested

## How It Works

1. Detect content format (PDF, HTML, plain text)
2. Extract metadata (title, authors, date, DOI, abstract)
3. Split into sections (introduction, methods, results, discussion, references)
4. Extract inline citations and build reference list
5. Store parsed output in `data/parsed/` as structured JSON
6. Advance status to `parsed`

## Decision Tree

```
For each ingested item:
  ├── Format detection fails? → Mark rejected (unreadable)
  ├── PDF scan-only (no text layer)? → Attempt OCR, else reject
  ├── Metadata extraction partial? → Continue with available fields
  ├── Section splitting fails? → Store as single body section
  └── All extractions succeed? → Advance to "parsed"
```

## Error Handling

- **PDF parse error**: Try alternative parser, then fall back to plain text extraction
- **Encoding issues**: Detect charset, convert to UTF-8
- **Timeout on large documents**: Skip, log warning, continue pipeline
