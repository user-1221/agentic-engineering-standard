# 10 — Agentignore: `.agentignore`

The `.agentignore` file tells agents which files they should never read or modify. It's the safety net — complementing `permissions.yaml` with a simpler, file-focused exclusion list.

## Location

`.agentignore` — at the project root (same level as `.gitignore`).

## Syntax

Same as `.gitignore`:

```
# Comment
pattern              # Exclude files matching pattern
!pattern             # Re-include a previously excluded pattern
dir/                 # Exclude entire directory
*.ext                # Wildcard matching
**/pattern           # Match in any directory
```

## Default Template

```
# ── Secrets ───────────────────────────────────────────────
.env
.env.*
*.pem
*.key
*.p12
credentials.json
service-account.json

# ── Databases ─────────────────────────────────────────────
*.sqlite3
*.db
*.sqlite

# ── Binary Artifacts ──────────────────────────────────────
*.cbm
*.joblib
*.pkl
*.h5
*.pt
*.onnx
models/**/*.json
*.bin

# ── Large Data ────────────────────────────────────────────
data/**/*.parquet
data/**/*.csv
data/**/*.tsv
*.arrow

# ── Build Artifacts ───────────────────────────────────────
dist/
build/
*.egg-info/
node_modules/
target/
__pycache__/
*.pyc
*.pyo

# ── System ────────────────────────────────────────────────
.git/
.DS_Store
Thumbs.db

# ── Agent Session Data ────────────────────────────────────
.agent/memory/sessions/
```

## Relationship to permissions.yaml

| File | Purpose | Granularity |
|------|---------|-------------|
| `.agentignore` | Files to skip entirely | File patterns |
| `permissions.yaml` | What actions are allowed/denied | Actions + files |

`.agentignore` is simpler — it's a blocklist of files. `permissions.yaml` is richer — it controls what the agent can do with files (read vs. write vs. delete) and also covers shell commands and domain actions.

Use `.agentignore` for: files that should never be read (secrets, binaries, large data).
Use `permissions.yaml` for: actions that need fine-grained control.

## When Agents Use It

Before reading any file, the agent should check `.agentignore`. If the file matches a pattern, skip it. This prevents:

- Accidentally reading secrets into context
- Wasting context window on binary files
- Processing large data files that don't fit in memory
- Reading build artifacts that aren't source code

## Generation

```bash
aes init    # generates a default .agentignore
```

The `aes init` command generates a `.agentignore` tailored to the project's language (Python, Node.js, Rust, Go, etc.).
