#!/bin/bash
# =============================================================================
# init-letsencrypt.sh — First-time Let's Encrypt SSL certificate setup
#
# Run this ONCE on a fresh server BEFORE starting production services.
# After this script completes successfully, use:
#   make prod-up
#
# Prerequisites:
#   - Ports 80 and 443 open on the server firewall
#   - DNS A records for DOMAIN and www.DOMAIN pointing to this server
#   - .env file present with all required variables
# =============================================================================
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
DOMAIN="${DOMAIN:-platanus.uz}"
EMAIL="${CERTBOT_EMAIL:-}"          # read from env or set below
STAGING="${STAGING:-0}"             # set STAGING=1 to test without rate-limit
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

if [ -z "$EMAIL" ]; then
  echo "ERROR: CERTBOT_EMAIL environment variable is not set."
  echo "Usage: CERTBOT_EMAIL=admin@example.com bash scripts/init-letsencrypt.sh"
  exit 1
fi

CERTBOT_CONF="$(pwd)/compose/production/certbot/conf"
CERTBOT_WWW="$(pwd)/compose/production/certbot/www"

# ── Helper: check Docker is running ──────────────────────────────────────────
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker is not running."
  exit 1
fi

echo "============================================================"
echo "  Domain : $DOMAIN"
echo "  Email  : $EMAIL"
echo "  Staging: $STAGING"
echo "============================================================"
echo ""

# ── Step 1: Create required directories ──────────────────────────────────────
echo "[1/5] Creating certbot directories ..."
mkdir -p "$CERTBOT_CONF/live/$DOMAIN"
mkdir -p "$CERTBOT_WWW"

# ── Step 2: Generate dummy self-signed certificate ───────────────────────────
# Nginx needs *some* cert to start, even before the real one exists.
echo "[2/5] Generating temporary self-signed certificate ..."
docker run --rm \
  -v "${CERTBOT_CONF}:/etc/letsencrypt" \
  --entrypoint openssl \
  certbot/certbot \
    req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" \
    -out    "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" \
    -subj   "/CN=${DOMAIN}"

# ── Step 3: Start nginx with dummy cert ──────────────────────────────────────
echo "[3/5] Starting Nginx with temporary certificate ..."
$COMPOSE up --force-recreate -d nginx

# Give nginx a moment to initialise
sleep 3

# ── Step 4: Obtain real certificate from Let's Encrypt ───────────────────────
echo "[4/5] Requesting certificate from Let's Encrypt ..."

STAGING_FLAG=""
if [ "$STAGING" = "1" ]; then
  STAGING_FLAG="--staging"
  echo "  (staging mode — certificate will NOT be trusted by browsers)"
fi

$COMPOSE run --rm --no-deps certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  $STAGING_FLAG \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN" \
  -d "www.$DOMAIN"

# ── Step 5: Reload nginx with real certificate ────────────────────────────────
echo "[5/5] Reloading Nginx with real certificate ..."
$COMPOSE exec nginx nginx -s reload

echo ""
echo "============================================================"
echo "  SSL certificate obtained successfully!"
echo "  Site is now live at: https://$DOMAIN"
echo ""
echo "  Next steps:"
echo "    make prod-up    — start all services"
echo "============================================================"
