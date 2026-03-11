# Skill: Display Results

## Purpose

Generate reports, summaries, and dashboards from organized content. Produces the final output of the research pipeline.

## When to Run

- Items at `organized` status are ready for output
- User requests a report or summary
- After a batch of items completes the pipeline

## How It Works

1. Collect all `organized` items (or filter by topic/date)
2. Group by taxonomy categories
3. Generate output in requested format (markdown, HTML, JSON)
4. Include cross-references as hyperlinks or citations
5. Write to `output/` directory
6. Advance included items to `displayed` status

## Decision Tree

```
Generate report:
  ├── No organized items? → Report empty, log warning
  ├── Topic filter active? → Include only matching categories
  ├── Format = markdown? → Generate .md with ToC and sections
  ├── Format = html? → Generate .html with navigation and styling
  ├── Format = json? → Generate structured .json for programmatic use
  └── Write to output/ → Advance items to "displayed"
```

## Error Handling

- **Template rendering failure**: Fall back to plain text output
- **Output directory missing**: Create it automatically
- **Large report (>1000 items)**: Paginate or generate index with per-category files
