# AES Registry Server — User Guide

This guide walks through everything you need to set up, operate, and maintain an AES package registry on your own server.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Part 1: Building the Server](#part-1-building-the-server)
- [Part 2: Local Testing](#part-2-local-testing)
- [Part 3: VPS Deployment](#part-3-vps-deployment)
- [Part 4: Docker Deployment](#part-4-docker-deployment)
- [Part 5: Using the Registry](#part-5-using-the-registry)
- [Part 6: Token Management](#part-6-token-management)
- [Part 7: Monitoring and Logs](#part-7-monitoring-and-logs)
- [Part 8: Backup and Recovery](#part-8-backup-and-recovery)
- [Part 9: Upgrading](#part-9-upgrading)
- [Part 10: Troubleshooting](#part-10-troubleshooting)

---

## Prerequisites

**To build the server:**
- Go 1.22 or later (`go version` to check)
- Make (optional, for convenience)

**To deploy on a VPS:**
- A Linux VPS (Ubuntu 22.04+ or Debian 12+ recommended)
- A domain name pointing to your VPS IP
- Root or sudo access

**To use the registry:**
- The `aes` CLI (`pip install aes-cli` or `cd cli && pip install -e .`)

---

## Part 1: Building the Server

### From source

```bash
cd server

# Build for Linux (for VPS deployment)
make build
# Output: ./aes-registry (statically linked, ~8 MB)

# Build for macOS (for local testing)
make build-darwin
# Output: ./aes-registry-darwin
```

### Cross-compilation

The Makefile builds for Linux amd64 by default. To target other platforms:

```bash
# Linux ARM64 (e.g., AWS Graviton, Oracle ARM instances)
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o aes-registry .

# FreeBSD
CGO_ENABLED=0 GOOS=freebsd GOARCH=amd64 go build -ldflags="-s -w" -o aes-registry .
```

### Verify the build

```bash
./aes-registry version
# aes-registry dev

./aes-registry help
```

---

## Part 2: Local Testing

Before deploying to a VPS, test everything locally.

### Step 1: Create a token

```bash
cd server
./aes-registry token create --name local-test
```

Output:
```
Token created. Save this — it will not be shown again:

  export AES_REGISTRY_KEY=aes_tok_7f3a9b2c4d5e6f...
```

Copy the `export` line and run it in your shell.

### Step 2: Start the server

```bash
./aes-registry serve
```

The server starts on `127.0.0.1:8080`. You'll see a log line:
```json
{"event":"server_start","address":"127.0.0.1:8080","version":"dev","level":"info","ts":"..."}
```

Leave this running and open a second terminal.

### Step 3: Verify with curl

```bash
# Health check
curl http://localhost:8080/health
# {"status":"ok","version":"dev"}

# Empty index
curl http://localhost:8080/index.json
# {"packages":{}}
```

### Step 4: Publish a test skill

Point the AES CLI at your local server:

```bash
export AES_REGISTRY_URL=http://localhost:8080
export AES_REGISTRY_KEY=aes_tok_...  # from step 1
```

If you have the AES examples checked out:

```bash
# Publish the "train" skill from the ML pipeline example
aes publish --skill train --registry --path examples/ml-pipeline -o /tmp/aes-dist
```

Or manually with curl:

```bash
# Create a minimal tarball
mkdir -p /tmp/test-skill/test
cat > /tmp/test-skill/test/skill.yaml << 'EOF'
aes_skill: "1.0"
id: test
name: Test Skill
version: 1.0.0
description: A test skill
EOF
cat > /tmp/test-skill/test/runbook.md << 'EOF'
# Test Skill
This is a test.
EOF
cd /tmp/test-skill && tar czf /tmp/test-1.0.0.tar.gz test/

# Upload
curl -X PUT http://localhost:8080/packages/test/1.0.0.tar.gz \
  -H "Authorization: Bearer $AES_REGISTRY_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/test-1.0.0.tar.gz
# {"status":"created","package":"test","version":"1.0.0"}
```

### Step 5: Search and install

```bash
# Search
aes search "test"

# Install into a test project
mkdir -p /tmp/test-project/.agent
aes install aes-hub/test@1.0.0 --path /tmp/test-project
```

### Step 6: Clean up

Stop the server with Ctrl+C. Remove test files:

```bash
rm -rf data backups audit.log tokens.json
```

---

## Part 3: VPS Deployment

### Step 1: Prepare the binary

On your local machine:

```bash
cd server
make build    # builds Linux amd64 binary
```

### Step 2: Transfer files to VPS

```bash
scp aes-registry user@your-vps:/tmp/
scp -r deploy/ user@your-vps:/tmp/deploy/
```

### Step 3: Run the setup script

SSH into your VPS:

```bash
ssh user@your-vps
sudo bash /tmp/deploy/setup.sh /tmp/aes-registry
```

The setup script:
1. Creates a dedicated `aes-registry` system user (no login shell, no home directory)
2. Creates `/var/lib/aes-registry/` with subdirectories for data, backups, tokens
3. Sets restrictive file permissions (tokens file is `chmod 600`)
4. Installs the binary to `/usr/local/bin/aes-registry`
5. Creates the environment config at `/etc/aes-registry/env`
6. Installs and enables the systemd unit

### Step 4: Create an admin token

```bash
sudo aes-registry token create --name admin
```

**Save the output.** The raw token is shown only once. You'll need it as `AES_REGISTRY_KEY` on your local machine.

### Step 5: Start the service

```bash
sudo systemctl start aes-registry
sudo systemctl status aes-registry
```

You should see "active (running)". Test locally on the VPS:

```bash
curl http://localhost:8080/health
# {"status":"ok","version":"1.0.0"}
```

### Step 6: Set up nginx

Install nginx and certbot:

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

Copy and configure the nginx config:

```bash
sudo cp /tmp/deploy/nginx.conf /etc/nginx/sites-available/aes-registry
```

Edit the file — replace every occurrence of `registry.yourdomain.com` with your actual domain:

```bash
sudo nano /etc/nginx/sites-available/aes-registry
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/aes-registry /etc/nginx/sites-enabled/
sudo nginx -t                  # test config
sudo systemctl reload nginx
```

### Step 7: Get a TLS certificate

```bash
sudo certbot --nginx -d registry.yourdomain.com
```

Certbot will:
- Obtain a Let's Encrypt certificate
- Configure nginx to use it
- Set up automatic renewal (runs twice daily via systemd timer)

### Step 8: Verify

From your local machine:

```bash
curl https://registry.yourdomain.com/health
# {"status":"ok","version":"1.0.0"}

curl https://registry.yourdomain.com/index.json
# {"packages":{}}
```

### Step 9: Configure the CLI

Add to your shell profile (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
export AES_REGISTRY_URL=https://registry.yourdomain.com
export AES_REGISTRY_KEY=aes_tok_...   # the token from step 4
```

Reload your shell and test:

```bash
aes search          # should return empty results (no packages yet)
```

---

## Part 4: Docker Deployment

If you prefer Docker over bare-metal:

### Step 1: Build the image

```bash
cd server
docker build -t aes-registry:latest .
```

### Step 2: Create a data volume and initialize

```bash
docker volume create aes-data

# Initialize with a token
docker run --rm -it \
  -v aes-data:/data \
  -e AES_REGISTRY_TOKENS_FILE=/data/tokens.json \
  aes-registry:latest token create --name admin
```

### Step 3: Run the container

```bash
docker run -d \
  --name aes-registry \
  --restart unless-stopped \
  -p 127.0.0.1:8080:8080 \
  -v aes-data:/data \
  -e AES_REGISTRY_DATA_DIR=/data/data \
  -e AES_REGISTRY_TOKENS_FILE=/data/tokens.json \
  -e AES_REGISTRY_AUDIT_LOG=/data/audit.log \
  -e AES_REGISTRY_BACKUP_DIR=/data/backups \
  -e AES_REGISTRY_LISTEN=0.0.0.0:8080 \
  aes-registry:latest
```

Note: Inside the container, the server binds to `0.0.0.0:8080`. The Docker port mapping `-p 127.0.0.1:8080:8080` ensures it's only accessible from localhost on the host. Always put nginx in front for TLS.

### Step 4: Set up nginx + TLS

Same as [VPS Deployment Step 6-7](#step-6-set-up-nginx).

### Docker Compose

For convenience, create `docker-compose.yml`:

```yaml
version: "3.8"
services:
  registry:
    build: .
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - aes-data:/data
    environment:
      AES_REGISTRY_DATA_DIR: /data/data
      AES_REGISTRY_TOKENS_FILE: /data/tokens.json
      AES_REGISTRY_AUDIT_LOG: /data/audit.log
      AES_REGISTRY_BACKUP_DIR: /data/backups
      AES_REGISTRY_LISTEN: "0.0.0.0:8080"
    restart: unless-stopped

volumes:
  aes-data:
```

```bash
docker compose up -d
```

---

## Part 5: Using the Registry

### Publishing Skills

The standard workflow for publishing a skill:

```bash
# 1. Make sure your project validates
aes validate --path ./my-project

# 2. Publish a specific skill to the registry
aes publish --skill deploy --registry --path ./my-project -o ./dist

# 3. Verify it's in the registry
aes search "deploy"
```

What happens during `aes publish --registry`:
1. The CLI packages the skill as a `.tar.gz` tarball
2. Uploads the tarball to `PUT /packages/{name}/{version}.tar.gz`
3. Fetches the current `index.json` from the registry
4. Adds the new version entry (with SHA256 hash and timestamp)
5. Uploads the updated `index.json` to `PUT /index.json`

### Installing Skills

```bash
# Install latest compatible version
aes install aes-hub/deploy@^1.0.0

# Install exact version
aes install aes-hub/deploy@1.2.3

# Install with tilde (patch-level updates only)
aes install aes-hub/train@~2.0.0

# Install latest
aes install aes-hub/train@*
```

Installed skills go into `.agent/skills/vendor/`:

```
.agent/skills/
  vendor/
    aes-hub/
      deploy/
        skill.yaml
        runbook.md
```

### Searching

```bash
# Search by keyword (matches name and description)
aes search "deploy"

# Filter by tag
aes search --tag ml

# Filter by domain
aes search --domain devops

# List all packages
aes search
```

### Declaring Dependencies

In your `agent.yaml`, declare skill dependencies:

```yaml
dependencies:
  skills:
    "aes-hub/deploy": "^1.0.0"
    "aes-hub/monitoring": "~2.0.0"
```

Install all dependencies:

```bash
aes install --path ./my-project
```

### Version Resolution

| Syntax | Meaning | Example |
|--------|---------|---------|
| `"1.2.3"` | Exact version | Only 1.2.3 |
| `"^1.2.0"` | Compatible (same major) | >=1.2.0, <2.0.0 |
| `"~1.2.0"` | Patch-level only | >=1.2.0, <1.3.0 |
| `">=1.0.0"` | Minimum version | 1.0.0 or higher |
| `"*"` | Any version | Latest available |

---

## Part 6: Token Management

### Creating Tokens

```bash
# On the server (or via SSH)
aes-registry token create --name "hiro-laptop"
```

Output:
```
Token created. Save this — it will not be shown again:

  export AES_REGISTRY_KEY=aes_tok_7f3a9b2c4d5e6f...
```

**Important**: The raw token is displayed exactly once. If you lose it, revoke the old token and create a new one.

### Listing Tokens

```bash
aes-registry token list
```

Output:
```
NAME                 CREATED                  LAST USED                PACKAGES
admin                2026-03-04T10:00:00Z     2026-03-04T12:30:00Z     *
ci-pipeline          2026-03-04T10:05:00Z     2026-03-04T11:00:00Z     *
ml-team              2026-03-04T10:10:00Z     never                    [train-* evaluate-*]
```

This shows names, timestamps, and package restrictions — never raw tokens.

### Revoking Tokens

```bash
aes-registry token revoke --name "old-laptop"
# Token "old-laptop" revoked.
```

The token stops working immediately.

### Token Rotation

To rotate a token (e.g., scheduled rotation):

```bash
# 1. Create new token
aes-registry token create --name "hiro-laptop-v2"
# Update AES_REGISTRY_KEY in your environment

# 2. Revoke old token
aes-registry token revoke --name "hiro-laptop"
```

Create the new token first so there's no downtime window.

### Scoped Tokens

Tokens can be restricted to specific package name patterns. Edit `tokens.json` directly to add restrictions:

```json
{
  "tokens": [
    {
      "hash": "sha256:...",
      "name": "ml-team",
      "created_at": "2026-03-04T10:00:00Z",
      "scopes": ["publish"],
      "allowed_packages": ["train-*", "evaluate-*", "preprocess-*"]
    }
  ]
}
```

With this configuration, the `ml-team` token can only publish packages whose names start with `train-`, `evaluate-`, or `preprocess-`. Attempts to publish other packages return 403 Forbidden.

### Best Practices

- **One token per person/system.** Don't share tokens between people or CI systems.
- **Use descriptive names.** `hiro-laptop`, `github-actions`, `ml-team` — not `token1`, `token2`.
- **Revoke immediately** when a token is compromised or a team member leaves.
- **Rotate periodically** for long-lived tokens (quarterly is a good cadence).
- **Use scoped tokens** when different teams publish different packages.

---

## Part 7: Monitoring and Logs

### Server Logs

The server writes structured JSON logs to stdout. When running under systemd, these are captured by the journal:

```bash
# View recent logs
sudo journalctl -u aes-registry -f

# View logs from the last hour
sudo journalctl -u aes-registry --since "1 hour ago"

# Filter for errors only
sudo journalctl -u aes-registry | grep '"level":"error"'

# Filter for security events
sudo journalctl -u aes-registry | grep '"level":"warn"'
```

### Log Format

Every request produces a log entry:

```json
{
  "ts": "2026-03-04T12:30:00.123Z",
  "level": "info",
  "method": "PUT",
  "path": "/packages/deploy/1.0.0.tar.gz",
  "status": 201,
  "duration_ms": 45,
  "bytes_out": 56,
  "ip": "203.0.113.42",
  "user_agent": "Python-urllib/3.11"
}
```

### Security Events

These are logged at `warn` level:

| Event | Meaning |
|-------|---------|
| `auth_failure` | Invalid token presented |
| `auth_blocked` | IP blocked due to too many auth failures |

Example:
```json
{"event":"auth_failure","ip":"203.0.113.42","blocked":false,"level":"warn","ts":"..."}
```

### Audit Log

Write operations are recorded in a separate append-only audit log:

```bash
cat /var/lib/aes-registry/audit.log
```

```json
{"action":"put_package","package":"deploy","version":"1.0.0","token_name":"admin","ip":"203.0.113.42","bytes":2048,"ts":"..."}
{"action":"put_index","token_name":"admin","ip":"203.0.113.42","bytes":1024,"ts":"..."}
```

This file records every upload and index update with: who did it (token name), from where (IP), and when.

### Health Monitoring

Set up an uptime monitor (UptimeRobot, Healthchecks.io, or any HTTP monitor) pointing at:

```
https://registry.yourdomain.com/health
```

Expected response: `{"status":"ok","version":"..."}` with HTTP 200.

### Log Rotation

The audit log grows over time. Set up logrotate:

```bash
sudo cat > /etc/logrotate.d/aes-registry << 'EOF'
/var/lib/aes-registry/audit.log {
    weekly
    rotate 52
    compress
    delaycompress
    missingok
    notifempty
    create 640 aes-registry aes-registry
}
EOF
```

This keeps 52 weeks of compressed audit logs.

---

## Part 8: Backup and Recovery

### What to Back Up

| Path | Contents | Priority |
|------|----------|----------|
| `/var/lib/aes-registry/data/` | index.json + all tarballs | Critical |
| `/var/lib/aes-registry/tokens.json` | Auth token hashes | Critical |
| `/etc/aes-registry/env` | Server configuration | Important |

The `backups/` and `audit.log` directories are useful but reconstructible.

### Automatic Backups

Add a daily cron job to sync data to a remote location:

```bash
# /etc/cron.d/aes-registry-backup
0 3 * * * root rsync -az /var/lib/aes-registry/data/ backup-server:/backups/aes-registry/data/
0 3 * * * root cp /var/lib/aes-registry/tokens.json /backups/aes-registry/tokens.json
```

Or use your VPS provider's snapshot feature (Hetzner, DigitalOcean, Linode all offer automatic daily snapshots).

### Recovery from Backup

If you need to restore:

```bash
# Stop the service
sudo systemctl stop aes-registry

# Restore data
sudo rsync -az backup-server:/backups/aes-registry/data/ /var/lib/aes-registry/data/
sudo cp /backups/aes-registry/tokens.json /var/lib/aes-registry/tokens.json

# Fix permissions
sudo chown -R aes-registry:aes-registry /var/lib/aes-registry
sudo chmod 600 /var/lib/aes-registry/tokens.json

# Restart
sudo systemctl start aes-registry
```

### Recovery from Index Corruption

If only `index.json` is corrupted, the server keeps timestamped backups:

```bash
ls /var/lib/aes-registry/backups/
# index.json.2026-03-04T10-30-00Z
# index.json.2026-03-04T11-45-00Z
# index.json.2026-03-04T14-00-00Z

# Restore the last good copy
sudo systemctl stop aes-registry
sudo cp /var/lib/aes-registry/backups/index.json.2026-03-04T11-45-00Z \
        /var/lib/aes-registry/data/index.json
sudo chown aes-registry:aes-registry /var/lib/aes-registry/data/index.json
sudo systemctl start aes-registry
```

### Rebuilding the Index

If you have the tarballs but lost `index.json`, you can rebuild it by re-publishing each skill. The tarballs on disk are the source of truth — `index.json` is derived from them.

---

## Part 9: Upgrading

### Binary Upgrade

```bash
# Build new version
cd server && make build

# Transfer to VPS
scp aes-registry user@your-vps:/tmp/

# On VPS: replace binary and restart
ssh user@your-vps
sudo systemctl stop aes-registry
sudo cp /tmp/aes-registry /usr/local/bin/aes-registry
sudo chmod 755 /usr/local/bin/aes-registry
sudo systemctl start aes-registry

# Verify
curl https://registry.yourdomain.com/health
```

The server is stateless beyond the filesystem — there's no database migration or schema update to worry about.

### Docker Upgrade

```bash
docker build -t aes-registry:latest .
docker compose down
docker compose up -d
```

Data persists in the Docker volume.

---

## Part 10: Troubleshooting

### Server won't start

**Check the logs:**
```bash
sudo journalctl -u aes-registry -n 50
```

**Common causes:**
- Port already in use: Check `sudo lsof -i :8080`
- Permissions: `ls -la /var/lib/aes-registry/` — everything should be owned by `aes-registry`
- Missing directories: Run `sudo bash deploy/setup.sh` again

### Can't connect from outside

1. Check the server is running: `curl http://localhost:8080/health` on the VPS
2. Check nginx is running: `sudo systemctl status nginx`
3. Check nginx config: `sudo nginx -t`
4. Check firewall: `sudo ufw status` — ports 80 and 443 must be open
5. Check DNS: `dig registry.yourdomain.com` — should point to your VPS IP

### "401 Unauthorized" on publish

1. Verify your token: `echo $AES_REGISTRY_KEY` — should start with `aes_tok_`
2. Check the token exists on the server: `sudo -u aes-registry aes-registry token list`
3. Check for brute force lockout: Look for `auth_blocked` in logs

If locked out, wait 15 minutes or restart the server (lockout state is in-memory).

### "429 Too Many Requests"

You've hit a rate limit. Check the `Retry-After` header for how long to wait. Limits:

- GET /index.json: 60 requests per minute
- GET /packages/*: 30 requests per minute
- PUT /*: 10 requests per minute
- Auth failures: 5 per 15 minutes

If you need higher limits for CI/CD, adjust the constants in `handler.go` and rebuild.

### "409 Conflict" on publish

The version you're trying to publish already exists. Versions are immutable — bump the version number in your skill manifest and publish again.

### TLS certificate issues

```bash
# Check certificate status
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal

# Test auto-renewal
sudo certbot renew --dry-run
```

### Disk space

Check how much space the registry is using:

```bash
du -sh /var/lib/aes-registry/data/
du -sh /var/lib/aes-registry/backups/
```

Clean up old index backups if needed:

```bash
# Keep only the last 30 backups
cd /var/lib/aes-registry/backups
ls -t | tail -n +31 | xargs rm -f
```

### Resetting everything

Nuclear option — start fresh:

```bash
sudo systemctl stop aes-registry
sudo rm -rf /var/lib/aes-registry/data /var/lib/aes-registry/backups
sudo rm -f /var/lib/aes-registry/audit.log
# Keep tokens.json if you want to keep your tokens
sudo systemctl start aes-registry
# Server recreates data/ with empty index.json on startup
```
