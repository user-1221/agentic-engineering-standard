#!/bin/bash
# AES Registry — VPS Setup Script
# Run as root: sudo bash setup.sh
set -euo pipefail

BINARY_SRC="${1:-./aes-registry}"
DATA_DIR="/var/lib/aes-registry"
BIN_DIR="/usr/local/bin"
CONF_DIR="/etc/aes-registry"

echo "=== AES Registry Setup ==="

# 1. Create system user (no login shell, no home dir)
if ! id aes-registry &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin aes-registry
    echo "[+] Created system user: aes-registry"
else
    echo "[.] User aes-registry already exists"
fi

# 2. Create data directories
mkdir -p "$DATA_DIR"/{data/packages,backups}
echo '{"packages":{}}' > "$DATA_DIR/data/index.json" 2>/dev/null || true
[ ! -f "$DATA_DIR/tokens.json" ] && echo '{"tokens":[]}' > "$DATA_DIR/tokens.json"

# 3. Set ownership and permissions
chown -R aes-registry:aes-registry "$DATA_DIR"
chmod 750 "$DATA_DIR"
chmod 750 "$DATA_DIR/data"
chmod 640 "$DATA_DIR/data/index.json"
chmod 750 "$DATA_DIR/data/packages"
chmod 750 "$DATA_DIR/backups"
chmod 600 "$DATA_DIR/tokens.json"
echo "[+] Directories created with restrictive permissions"

# 4. Install binary
if [ -f "$BINARY_SRC" ]; then
    cp "$BINARY_SRC" "$BIN_DIR/aes-registry"
    chmod 755 "$BIN_DIR/aes-registry"
    echo "[+] Binary installed to $BIN_DIR/aes-registry"
else
    echo "[!] Binary not found at $BINARY_SRC — skipping install"
    echo "    Build with: cd server && make build"
    echo "    Then run: sudo bash setup.sh ./aes-registry"
fi

# 5. Create environment config
mkdir -p "$CONF_DIR"
if [ ! -f "$CONF_DIR/env" ]; then
    cat > "$CONF_DIR/env" << 'EOF'
AES_REGISTRY_DATA_DIR=/var/lib/aes-registry/data
AES_REGISTRY_TOKENS_FILE=/var/lib/aes-registry/tokens.json
AES_REGISTRY_AUDIT_LOG=/var/lib/aes-registry/audit.log
AES_REGISTRY_BACKUP_DIR=/var/lib/aes-registry/backups
AES_REGISTRY_LISTEN=127.0.0.1:8080
AES_REGISTRY_LOG_LEVEL=info
EOF
    chmod 600 "$CONF_DIR/env"
    echo "[+] Environment config created at $CONF_DIR/env"
else
    echo "[.] Environment config already exists"
fi

# 6. Install systemd unit
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/aes-registry.service" ]; then
    cp "$SCRIPT_DIR/aes-registry.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable aes-registry
    echo "[+] systemd unit installed and enabled"
else
    echo "[!] aes-registry.service not found — copy it manually to /etc/systemd/system/"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Create an auth token:"
echo "     sudo -u aes-registry aes-registry token create --name admin"
echo ""
echo "  2. Start the service:"
echo "     sudo systemctl start aes-registry"
echo ""
echo "  3. Set up nginx + TLS:"
echo "     sudo apt install nginx certbot python3-certbot-nginx"
echo "     sudo cp deploy/nginx.conf /etc/nginx/sites-available/aes-registry"
echo "     # Edit the file: replace registry.yourdomain.com with your domain"
echo "     sudo ln -s /etc/nginx/sites-available/aes-registry /etc/nginx/sites-enabled/"
echo "     sudo certbot --nginx -d registry.yourdomain.com"
echo ""
echo "  4. Verify:"
echo "     curl https://registry.yourdomain.com/health"
