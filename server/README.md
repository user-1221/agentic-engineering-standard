# AES Registry Server

Self-hosted package registry for the [Agentic Engineering Standard](../README.md). A single Go binary that stores and serves AES skill packages over HTTP with bearer token authentication.

## Overview

The AES registry is an authenticated file server. It stores two things:

1. **`index.json`** — a JSON catalog of all published skill packages
2. **Tarballs** — `.tar.gz` archives of individual skill versions

The `aes` CLI handles all the complexity (version resolution, search filtering, SHA256 verification). The server just stores and serves files.

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [Getting Started](../GETTING-STARTED.md) | End users | Full workflow from zero: init, customize, sync, install, publish |
| [Admin Guide](docs/user-guide.md) | Server operators | VPS setup, deployment, token management, monitoring, backups |
| [Architecture](docs/architecture.md) | Contributors | System design, security model, internals, threat analysis |

## Quick Start

```bash
# Build (requires Go 1.22+)
cd server
make build                    # linux amd64 binary
make build-darwin             # macOS arm64 binary

# Create an auth token
./aes-registry token create --name admin
# Output: export AES_REGISTRY_KEY=aes_tok_...
# Save this token — it's shown only once.

# Start the server
./aes-registry serve
# Listening on 127.0.0.1:8080

# Verify
curl http://localhost:8080/health
# {"status":"ok","version":"dev"}
```

## API Reference

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | No | Health check — returns `{"status":"ok"}` |
| `GET` | `/index.json` | No | Full package catalog |
| `GET` | `/packages/{name}/{version}.tar.gz` | No | Download a skill tarball |
| `PUT` | `/packages/{name}/{version}.tar.gz` | Bearer | Upload a skill tarball |
| `PUT` | `/index.json` | Bearer | Update the package catalog |

### Authentication

Write endpoints require a bearer token in the `Authorization` header:

```
Authorization: Bearer aes_tok_7f3a9b2c...
```

Tokens are created with `aes-registry token create --name <name>` and set on the client via:

```bash
export AES_REGISTRY_KEY=aes_tok_7f3a9b2c...
```

### GET /health

Returns server status. No authentication required.

```bash
curl https://registry.example.com/health
```

```json
{"status": "ok", "version": "1.0.0"}
```

### GET /index.json

Returns the full package catalog. Cached for 60 seconds.

```bash
curl https://registry.example.com/index.json
```

```json
{
  "packages": {
    "deploy": {
      "description": "Deploy skill for AES projects",
      "latest": "1.1.0",
      "tags": ["devops", "deployment"],
      "versions": {
        "1.0.0": {
          "url": "packages/deploy/1.0.0.tar.gz",
          "sha256": "a1b2c3d4...",
          "published_at": "2026-03-01T12:00:00Z"
        },
        "1.1.0": {
          "url": "packages/deploy/1.1.0.tar.gz",
          "sha256": "e5f6a7b8...",
          "published_at": "2026-03-04T09:30:00Z"
        }
      }
    }
  }
}
```

### GET /packages/{name}/{version}.tar.gz

Downloads a skill tarball. Cached for 24 hours (immutable content).

```bash
curl -o deploy-1.0.0.tar.gz https://registry.example.com/packages/deploy/1.0.0.tar.gz
```

Returns 404 if the package or version doesn't exist.

### PUT /packages/{name}/{version}.tar.gz

Uploads a skill tarball. Requires authentication. Returns 409 if the version already exists (versions are immutable).

```bash
curl -X PUT https://registry.example.com/packages/deploy/1.0.0.tar.gz \
  -H "Authorization: Bearer $AES_REGISTRY_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @deploy-1.0.0.tar.gz
```

```json
{"status": "created", "package": "deploy", "version": "1.0.0"}
```

**Constraints:**
- Package name: lowercase letters, digits, hyphens, underscores. Must start with a letter. Max 64 chars.
- Version: semver format `MAJOR.MINOR.PATCH` (e.g., `1.0.0`).
- Max upload size: 50 MB (configurable).
- Immutable: once published, a version cannot be overwritten.

### PUT /index.json

Updates the package catalog. Requires authentication. The server validates the JSON structure before accepting.

```bash
curl -X PUT https://registry.example.com/index.json \
  -H "Authorization: Bearer $AES_REGISTRY_KEY" \
  -H "Content-Type: application/json" \
  -d @index.json
```

The previous index is backed up before overwriting.

### Error Responses

All errors return JSON:

```json
{"error": "description of the problem"}
```

| Code | Meaning |
|------|---------|
| 400 | Invalid input (bad name, version, JSON) |
| 401 | Missing or invalid auth token |
| 403 | Token not authorized for this package |
| 404 | Package or version not found |
| 409 | Version already exists (immutability) |
| 413 | Upload too large |
| 429 | Rate limit exceeded (check `Retry-After` header) |

## CLI Commands

### `aes-registry serve`

Starts the HTTP server. Reads all configuration from environment variables.

### `aes-registry token create --name <name>`

Creates a new auth token. Prints the raw token exactly once — it is never stored or shown again. The server stores only the SHA256 hash.

### `aes-registry token list`

Lists all tokens with their names, creation dates, and last-used timestamps. Never shows raw tokens.

### `aes-registry token revoke --name <name>`

Revokes a token by name. The token immediately stops working.

### `aes-registry version`

Prints the server version.

## Configuration Reference

All configuration is via environment variables with sensible defaults.

| Variable | Default | Description |
|----------|---------|-------------|
| `AES_REGISTRY_LISTEN` | `127.0.0.1:8080` | Bind address. Use `127.0.0.1` when behind nginx. |
| `AES_REGISTRY_DATA_DIR` | `./data` | Root directory for index.json and packages. |
| `AES_REGISTRY_TOKENS_FILE` | `./tokens.json` | Path to the hashed tokens file. |
| `AES_REGISTRY_AUDIT_LOG` | `./audit.log` | Path to the append-only audit log. |
| `AES_REGISTRY_BACKUP_DIR` | `./backups` | Directory for index.json backups. |
| `AES_REGISTRY_MAX_PACKAGE_SIZE` | `52428800` | Max tarball upload in bytes (default 50 MB). |
| `AES_REGISTRY_MAX_INDEX_SIZE` | `5242880` | Max index.json upload in bytes (default 5 MB). |
| `AES_REGISTRY_LOG_LEVEL` | `info` | Log verbosity: `debug`, `info`, `warn`, `error`. |

## Using with the AES CLI

Once your registry is running:

```bash
# Point the CLI at your registry
export AES_REGISTRY_URL=https://registry.yourdomain.com
export AES_REGISTRY_KEY=aes_tok_...

# Publish a skill
aes publish --skill train --registry --path ./my-project

# Search for skills
aes search "deploy"
aes search --tag ml
aes search --domain devops

# Install a skill
aes install aes-hub/deploy@^1.0.0
aes install aes-hub/train@~2.0.0
```

Version specifiers: exact (`1.2.3`), caret (`^1.2.0`), tilde (`~1.2.0`), minimum (`>=1.0.0`), wildcard (`*`).

## Security Summary

See [Architecture](docs/architecture.md) for the full security analysis.

- **Authentication**: Bearer tokens stored as SHA256 hashes, constant-time comparison
- **Brute force protection**: 5 failures per IP → 15-minute lockout
- **Rate limiting**: Per-endpoint limits (60/30/10 req/min) + nginx global limit
- **Immutability**: Published versions cannot be overwritten (409 Conflict)
- **Path traversal**: 3-layer defense (regex, filepath.Clean, prefix containment check)
- **Atomic writes**: Temp file + rename — no partial reads possible
- **Index backups**: Timestamped copy before every index.json update
- **Token scoping**: Optional per-token package name restrictions
- **Process isolation**: systemd sandboxing (ProtectSystem=strict, NoNewPrivileges)
- **TLS**: nginx reverse proxy with Let's Encrypt auto-renewal

## License

MIT
