# AES Registry Server — Architecture and Security

This document covers the system design, security model, and threat analysis for the AES registry server.

## Table of Contents

- [System Overview](#system-overview)
- [Design Decisions](#design-decisions)
- [Request Flow](#request-flow)
- [Storage Model](#storage-model)
- [Authentication Model](#authentication-model)
- [Security Hardening](#security-hardening)
- [Threat Analysis](#threat-analysis)
- [Source Code Map](#source-code-map)

---

## System Overview

The AES registry is an **authenticated file server**. It stores skill packages (tarballs) and a package catalog (index.json), and serves them over HTTP. All intelligence — version resolution, search, dependency management, integrity verification — lives in the client (`aes` CLI). The server is deliberately simple.

```
                                    ┌─────────────────────────┐
                                    │       VPS               │
                                    │                         │
┌──────────┐     HTTPS     ┌────────┤──────┐    HTTP    ┌─────┤─────────┐
│ aes CLI  │ ────────────> │ nginx  │      │ ────────> │ aes-registry  │
│ (client) │ <──────────── │ :443   │      │ <──────── │ :8080         │
└──────────┘               └────────┤──────┘           └─────┤─────────┘
                                    │                        │
                                    │                  ┌─────┤─────────┐
                                    │                  │ /var/lib/     │
                                    │                  │ aes-registry/ │
                                    │                  │   data/       │
                                    │                  │   tokens.json │
                                    │                  │   audit.log   │
                                    │                  │   backups/    │
                                    │                  └───────────────┘
                                    └─────────────────────────┘
```

**Why Go?** Single static binary with no runtime dependencies. Cross-compiles from macOS to Linux with one command. Uses ~10-20 MB of RAM at idle. The Go standard library includes a production-grade HTTP server — no framework needed.

**Why not Python?** The CLI is Python, but the server is infrastructure. Infrastructure favors single-binary deployment, minimal resource usage, and zero-dependency operation. A Python server would require a virtualenv, a WSGI server (gunicorn/uvicorn), and more memory.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Go | Single binary, minimal resources, production-grade stdlib HTTP |
| TLS termination | nginx | Battle-tested, auto-renewing Let's Encrypt, separates concerns |
| Storage | Filesystem | No database needed — data is files. Simple to backup, inspect, restore. |
| Auth | Bearer tokens | Matches the existing CLI protocol. Simple, stateless per-request. |
| Token storage | SHA256 hashes | Raw tokens never persisted. Leaked tokens.json doesn't compromise auth. |
| Rate limiting | In-process + nginx | Two layers: nginx for volumetric DDoS, Go for per-endpoint limits |
| Version immutability | Enforced | Critical for supply chain security. Once published, never changes. |
| Index writes | Mutex-serialized | Prevents lost updates from concurrent publishes |
| File writes | Atomic (temp + rename) | No partial writes visible to concurrent readers |
| Logging | Structured JSON | Machine-parseable, easy to filter, works with any log aggregator |

---

## Request Flow

Every request passes through the following chain:

```
Client Request
    │
    ▼
┌─────────────────────────┐
│ nginx (reverse proxy)   │  TLS termination, global rate limit (20 req/s),
│                         │  client_max_body_size 50m, X-Real-IP header
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Logging middleware       │  Structured JSON: method, path, status, duration,
│                         │  bytes, IP, user-agent
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ CORS middleware          │  Access-Control-Allow-Origin: *
│                         │  Access-Control-Allow-Methods: GET, PUT, OPTIONS
│                         │  OPTIONS → 204 (preflight)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Route matching           │  GET /health        → handleHealth
│                         │  GET /index.json    → rate limit → handleGetIndex
│                         │  GET /packages/*    → rate limit → handleGetPackage
│                         │  PUT /index.json    → rate limit → handlePutIndex
│                         │  PUT /packages/*    → rate limit → handlePutPackage
└────────────┬────────────┘
             │
             ▼ (for PUT endpoints)
┌─────────────────────────┐
│ Authentication           │  Check brute force lockout
│                         │  Extract Bearer token
│                         │  SHA256 hash → constant-time compare
│                         │  Record failure if invalid
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Input validation         │  Name: ^[a-z][a-z0-9_-]{0,63}$
│                         │  Version: ^\d{1,5}\.\d{1,5}\.\d{1,5}$
│                         │  Content-Type, body size, JSON structure
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Storage operation        │  Read or write file (atomic)
│                         │  Path containment check
│                         │  Immutability check (for PUT packages)
│                         │  Backup-on-write (for PUT index)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Audit log (PUT only)     │  Action, package, version, token name, IP, bytes
└─────────────────────────┘
```

---

## Storage Model

### Directory Layout

```
/var/lib/aes-registry/
├── data/                           # Served files (1:1 URL mapping)
│   ├── index.json                  # Package catalog
│   └── packages/
│       ├── deploy/
│       │   ├── 1.0.0.tar.gz
│       │   └── 1.1.0.tar.gz
│       └── train/
│           └── 2.0.0.tar.gz
├── backups/                        # Index snapshots (automatic)
│   ├── index.json.2026-03-04T10-30-00Z
│   └── index.json.2026-03-04T14-00-00Z
├── tokens.json                     # Hashed auth tokens (chmod 600)
└── audit.log                       # Append-only write log
```

### URL-to-Path Mapping

The URL path maps directly to the filesystem:

| URL | Filesystem Path |
|-----|-----------------|
| `GET /index.json` | `data/index.json` |
| `GET /packages/deploy/1.0.0.tar.gz` | `data/packages/deploy/1.0.0.tar.gz` |

This 1:1 mapping means:
- You can inspect the registry by browsing the filesystem
- Backup is just `rsync` or `cp`
- Disaster recovery is just restoring files
- No database, no migration, no schema

### Atomic Writes

All file writes follow the pattern:

1. Write to a temporary file in the same directory (`.tmp-*`)
2. `chmod` the temp file to the correct permissions
3. `os.Rename` the temp file to the final path (atomic on POSIX)

This guarantees that readers never see partial writes. If the server crashes mid-write, only the temp file is left behind — the original file is untouched.

### Index Backup-on-Write

Every time `index.json` is updated via PUT:

1. The current `index.json` is copied to `backups/index.json.<timestamp>`
2. The new content is validated (valid JSON, correct structure)
3. The new content is atomically written to `data/index.json`

This provides an automatic audit trail of every index change and simple rollback capability.

### Version Immutability

Once `data/packages/{name}/{version}.tar.gz` exists, it cannot be overwritten. A PUT to an existing path returns **409 Conflict**. This is the most important security property:

- Clients that downloaded `deploy@1.0.0` yesterday will get the same bytes today
- A compromised auth token cannot silently replace a published package
- The SHA256 in `index.json` matches the tarball permanently
- Supply chain attacks via version replacement are structurally prevented

---

## Authentication Model

### Token Lifecycle

```
Create                              Validate
┌──────────┐                        ┌──────────┐
│ Generate  │  32 bytes             │ Receive   │  Bearer token from
│ random    │  crypto/rand          │ token     │  Authorization header
└────┬─────┘                        └────┬─────┘
     │                                   │
     ▼                                   ▼
┌──────────┐                        ┌──────────┐
│ Format   │  aes_tok_ + hex       │ SHA256    │  Hash the received
│ as token │  = 71 chars            │ hash      │  token
└────┬─────┘                        └────┬─────┘
     │                                   │
     ▼                                   ▼
┌──────────┐                        ┌──────────┐
│ SHA256   │  Hash the raw         │ Compare   │  Constant-time compare
│ hash     │  token                 │ to stored │  against all stored hashes
└────┬─────┘                        └────┬─────┘
     │                                   │
     ▼                                   ▼
┌──────────┐                        ┌──────────┐
│ Store    │  Only the hash        │ Accept or │  If match: return token entry
│ hash     │  in tokens.json       │ reject    │  If no match: record failure
└────┬─────┘                        └──────────┘
     │
     ▼
┌──────────┐
│ Print    │  Display raw token
│ once     │  to the user (never again)
└──────────┘
```

### Token Format

```
aes_tok_7f3a9b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f
└──────┘└──────────────────────────────────────────────────────────────────┘
 prefix   32 bytes of crypto/rand, hex-encoded (64 chars)
```

Total: 71 characters. The `aes_tok_` prefix makes tokens:
- Identifiable in logs and monitoring
- Detectable by secret scanners (GitHub, GitGuardian)
- Distinguishable from other credentials

### Token Storage

Tokens are stored in `tokens.json` as SHA256 hashes:

```json
{
  "tokens": [
    {
      "hash": "sha256:a1b2c3d4e5f6...",
      "name": "admin",
      "created_at": "2026-03-04T10:00:00Z",
      "last_used": "2026-03-04T12:30:00Z",
      "scopes": ["publish"],
      "allowed_packages": []
    }
  ]
}
```

If this file is leaked:
- Attacker gets token names and metadata — **not** raw tokens
- SHA256 is one-way — the raw tokens cannot be recovered
- The attacker would need to brute-force 256 bits of entropy — computationally infeasible

### Constant-Time Comparison

Token validation uses `crypto/subtle.ConstantTimeCompare`. This prevents timing attacks where an attacker measures response time to determine how many bytes of a token hash are correct.

### Package Scoping

Each token can optionally restrict which packages it can publish to, via `allowed_packages` in `tokens.json`:

```json
"allowed_packages": ["train-*", "evaluate-*"]
```

The server matches the package name against each pattern using prefix glob matching. If `allowed_packages` is empty, the token has unrestricted access.

Use case: Give the ML team a token that can only publish `train-*` packages. Even if the token is compromised, the attacker can't publish to other package namespaces.

---

## Security Hardening

### 1. Rate Limiting

**Two layers:**

**Layer 1: nginx** — Global rate limit via `limit_req_zone`:
- 20 requests/second per IP, burst of 50
- Catches volumetric attacks before they reach the Go process
- Configured in `deploy/nginx.conf`

**Layer 2: Go server** — Per-endpoint rate limits:

| Endpoint | Limit | Window |
|----------|-------|--------|
| GET /index.json | 60 requests | per minute per IP |
| GET /packages/* | 30 requests | per minute per IP |
| PUT /* (writes) | 10 requests | per minute per IP |

When exceeded, the server returns **429 Too Many Requests** with a `Retry-After` header indicating how many seconds to wait.

Implementation: In-memory sliding window counter per IP, stored in a `sync.Mutex`-protected map. A background goroutine cleans up stale entries every 5 minutes to prevent memory growth.

### 2. Brute Force Protection

A dedicated rate limiter for authentication failures:

- **Threshold**: 5 failures per IP in 15 minutes
- **Action**: Block all authenticated requests from that IP for 15 minutes
- **Response**: 429 with `Retry-After: 900`
- **Reset**: The counter resets only when the 15-minute window expires. Successful authentication does not reset it (prevents an attacker from using a known valid token to reset the counter while brute-forcing other tokens).
- **Scope**: IP-based. Different IPs have independent counters.

With 256 bits of token entropy (32 bytes from `crypto/rand`), brute-forcing a token is computationally infeasible regardless of rate limiting. The brute force limiter exists as defense-in-depth.

### 3. Request Size Limits

| Endpoint | Max Body | Mechanism |
|----------|----------|-----------|
| PUT /packages/* | 50 MB | `http.MaxBytesReader` |
| PUT /index.json | 5 MB | `http.MaxBytesReader` |

`MaxBytesReader` wraps the request body and returns an error when the limit is exceeded, before the full body is read into memory. This prevents memory exhaustion attacks.

The limits are also enforced at the nginx layer via `client_max_body_size 50m`.

### 4. Path Traversal Prevention

Three layers of defense against path traversal attacks (e.g., `../../etc/passwd`):

**Layer 1 — Input validation**: Package names must match `^[a-z][a-z0-9_-]{0,63}$`. Versions must match `^\d{1,5}\.\d{1,5}\.\d{1,5}$`. These regexes structurally exclude `.`, `/`, `\`, null bytes, and any character that could escape the intended directory.

**Layer 2 — Path construction**: The server constructs paths using `filepath.Join(dataDir, "packages", name, version+".tar.gz")` followed by `filepath.Clean`. This normalizes the path and resolves any remaining `..` components.

**Layer 3 — Containment check**: After constructing the absolute path, the server verifies it is still under the data directory:

```go
absPath, _ := filepath.Abs(constructedPath)
absData, _ := filepath.Abs(dataDir + "/packages")
if !isSubpath(absPath, absData) {
    return error  // path traversal blocked
}
```

Even if layers 1 and 2 are somehow bypassed, layer 3 prevents any file access outside the data directory.

### 5. Symlink Protection

Before reading a file for download, the server calls `os.Lstat` (not `os.Stat`) and checks that the file is not a symlink. This prevents an attacker who gains filesystem access from creating symlinks that point outside the data directory.

### 6. Atomic Writes and Data Integrity

- All file writes use temp file + `os.Rename` (atomic on POSIX)
- `index.json` writes are serialized with `sync.Mutex` — no lost updates from concurrent publishes
- The previous `index.json` is backed up before every write
- The client verifies SHA256 hashes after every download (in `cli/aes/registry.py`)

### 7. TLS

- The Go server binds to `127.0.0.1:8080` — unreachable from the internet
- All external traffic goes through nginx, which terminates TLS
- Let's Encrypt provides free, auto-renewing certificates
- nginx is configured with TLS 1.2+, HSTS, and modern cipher suites

### 8. Process Isolation

The systemd unit applies extensive sandboxing:

| Directive | Effect |
|-----------|--------|
| `User=aes-registry` | Runs as a dedicated non-root user |
| `NoNewPrivileges=yes` | Cannot gain additional privileges |
| `ProtectSystem=strict` | Entire filesystem is read-only |
| `ReadWritePaths=/var/lib/aes-registry` | Only the data directory is writable |
| `ProtectHome=yes` | No access to /home, /root, /run/user |
| `PrivateTmp=yes` | Isolated /tmp |
| `PrivateDevices=yes` | No access to physical devices |
| `RestrictAddressFamilies=AF_INET AF_INET6` | Only TCP/IP networking |
| `MemoryDenyWriteExecute=yes` | Cannot create executable memory (prevents shellcode) |
| `SystemCallFilter=@system-service` | Only syscalls needed for a network service |
| `SystemCallArchitectures=native` | Only native syscalls (prevents 32-bit escape) |

Even if the Go process is fully compromised (RCE), the attacker is confined to the data directory with no ability to escalate privileges, access other files, or execute arbitrary code.

### 9. Structured Audit Trail

All write operations produce audit log entries with:
- Timestamp
- Action type (put_package or put_index)
- Package name and version (for package uploads)
- Token name (which credential was used)
- Client IP
- Bytes written

This provides non-repudiation — you can always trace who published what and when.

---

## Threat Analysis

### Threat: Stolen Auth Token

**Impact**: Attacker can publish new versions of packages.

**Mitigations**:
- Version immutability: Cannot replace existing published versions
- Package scoping: If the token is scoped, can only publish to allowed packages
- Audit log: All publishes are logged with token name, IP, and timestamp
- Token revocation: Immediately revoke the compromised token

**Detection**: Monitor the audit log for unexpected publishes (unknown IPs, unusual times).

### Threat: Brute Force Token Guessing

**Impact**: If successful, attacker gains publish access.

**Mitigations**:
- 256-bit token entropy: 2^256 possible tokens — computationally infeasible to guess
- Brute force limiter: 5 failures per IP → 15-minute lockout
- Per-endpoint rate limiting: 10 writes per minute per IP
- nginx global rate limit: 20 req/s

**Detection**: `auth_failure` and `auth_blocked` warn-level log entries.

### Threat: Denial of Service

**Impact**: Registry becomes unavailable.

**Mitigations**:
- nginx rate limiting (20 req/s with burst)
- Per-endpoint rate limiting in Go
- Request body size limits (50 MB max)
- Go server timeouts (Read: 30s, Write: 120s, Idle: 120s)
- The server is stateless — restart recovers immediately

**Detection**: High rate of 429 responses in logs. nginx connection logs.

### Threat: Path Traversal (File Read/Write Outside Data Dir)

**Impact**: Read sensitive files or overwrite system files.

**Mitigations**:
- Input regex blocks `.`, `/`, `\`, null bytes in names/versions
- `filepath.Clean` normalizes paths
- Containment check verifies resolved path is under data directory
- `os.Lstat` rejects symlinks
- systemd `ProtectSystem=strict` makes everything read-only except the data dir

**Detection**: Any request with unusual characters would fail validation and be logged.

### Threat: Supply Chain Attack (Package Tampering)

**Impact**: Users install malicious code.

**Mitigations**:
- Version immutability: Published tarballs cannot be overwritten
- SHA256 in index: Client verifies hash after every download
- Index backup: Previous index versions are preserved
- Token scoping: Limits which packages each token can publish

**Detection**: SHA256 mismatch errors on client side. Audit log shows all publishes.

### Threat: Server Compromise (Full RCE)

**Impact**: Attacker controls the server process.

**Mitigations**:
- systemd sandboxing: Read-only filesystem, no home access, restricted syscalls, no privilege escalation
- Dedicated user: No access to files outside `/var/lib/aes-registry`
- nginx fronts the server: Attacker can't intercept TLS or redirect traffic
- Tokens are hashed: Even with filesystem access, raw tokens aren't recoverable

**Recovery**: Stop the service, restore from backup, rotate all tokens, investigate the compromise vector.

### Threat: Man-in-the-Middle

**Impact**: Attacker intercepts or modifies packages in transit.

**Mitigations**:
- TLS via nginx + Let's Encrypt: All traffic is encrypted
- HSTS header: Browsers and HTTP clients remember to use HTTPS
- Client SHA256 verification: Even if TLS is somehow broken, tampered packages are detected

### Threat: Compression Bomb (Zip Bomb)

**Impact**: Extracting a malicious tarball consumes all disk/memory.

**Mitigations**:
- The server never extracts tarballs — they are stored as opaque blobs
- The client extracts tarballs with a safe extraction function that validates paths
- Upload size limit (50 MB) bounds the maximum compressed size

---

## Source Code Map

| File | Lines | Responsibility |
|------|-------|---------------|
| `config.go` | ~50 | Environment variable parsing, Config struct |
| `storage.go` | ~180 | Atomic file I/O, backup-on-write, path containment, symlink check |
| `validation.go` | ~100 | Name/version regex, index JSON structure validation |
| `auth.go` | ~220 | Token CRUD, SHA256 hashing, constant-time compare, brute force limiter |
| `middleware.go` | ~170 | Structured logger, CORS, rate limiter, response writer wrapper |
| `handler.go` | ~250 | 5 HTTP handlers, authentication, path parsing, JSON errors |
| `main.go` | ~160 | CLI (serve + token subcommands), HTTP server setup, graceful shutdown |

Total: ~1130 lines of Go (including tests).

### Key Functions

| Function | File | What It Does |
|----------|------|-------------|
| `NewStorage()` | storage.go | Initializes directories, creates empty index.json |
| `Storage.WritePackage()` | storage.go | Atomic write with immutability check and containment check |
| `Storage.WriteIndex()` | storage.go | Mutex-serialized, backup-on-write, atomic |
| `atomicWrite()` | storage.go | Temp file → chmod → rename |
| `isSubpath()` | storage.go | Path containment check |
| `TokenStore.CreateToken()` | auth.go | Generate random bytes, hash, store, return raw |
| `TokenStore.Validate()` | auth.go | Hash input, constant-time compare against all stored hashes |
| `BruteForceLimiter.RecordFailure()` | auth.go | Track auth failures per IP, block after threshold |
| `ValidateName()` | validation.go | Regex check for package names |
| `ValidateIndexJSON()` | validation.go | Structure validation for index.json uploads |
| `Server.authenticate()` | handler.go | Full auth flow: lockout check, token extraction, validation |
| `Server.handlePutPackage()` | handler.go | Auth → validate → immutability check → store → audit |
