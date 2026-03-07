# Skill: Publish Model

## Purpose

Upload the packaged model to HuggingFace Hub and register it with the metered prediction API.

## When to Run

- Dataset is at `packaged` status
- Package zip exists and is verified
- HF_TOKEN environment variable is set

## How It Works

1. Load package zip from package stage
2. Upload to HuggingFace Hub with model card
3. Register model with prediction API endpoint
4. Generate API key for metered access
5. Verify both platforms respond correctly
6. Advance to `published`

## Decision Tree

```
Publish to platforms:
  ├── HuggingFace upload
  │   ├── Success? → Record URL
  │   └── Failure? → Log error, continue to API
  ├── API registration
  │   ├── Success? → Record endpoint URL
  │   └── Failure? → Log error
  └── At least one succeeded? → Status: published
     └── Both failed? → Keep at packaged, log errors
```

## Error Handling

- **HF_TOKEN invalid**: Abort HF upload, try API only
- **Network error**: Retry once per platform
- **API registration failure**: Log and keep at packaged status
