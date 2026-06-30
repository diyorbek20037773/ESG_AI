#!/bin/bash
# =============================================================================
# health-check.sh — Production service health overview
#
# Usage:
#   bash scripts/health-check.sh
# =============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# ── Colours & helpers ─────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}✔${NC}  $*"; }
fail() { echo -e "  ${RED}✘${NC}  $*"; FAILED=$((FAILED+1)); }
warn() { echo -e "  ${YELLOW}!${NC}  $*"; }
sep()  { echo -e "${CYAN}────────────────────────────────────────────${NC}"; }

FAILED=0
cd "$PROJECT_DIR"

echo ""
echo -e "${BOLD}${CYAN}  Production Health Check — $(date -u '+%Y-%m-%d %H:%M UTC')${NC}"
sep

# ── 1. Docker containers ──────────────────────────────────────────────────────
echo -e "\n${BOLD}  Containers${NC}"
for SERVICE in db web nginx certbot; do
  STATUS=$($COMPOSE ps "$SERVICE" --format "{{.Status}}" 2>/dev/null | head -1 || echo "not found")
  HEALTH=$($COMPOSE ps "$SERVICE" --format "{{.Health}}" 2>/dev/null | head -1 || echo "")

  if echo "$STATUS" | grep -qi "up\|running"; then
    LABEL="$STATUS"
    [ -n "$HEALTH" ] && LABEL="$LABEL ($HEALTH)"
    if echo "$HEALTH" | grep -qi "unhealthy"; then
      fail "$SERVICE — $LABEL"
    else
      ok "$SERVICE — $LABEL"
    fi
  else
    if [ "$SERVICE" = "certbot" ]; then
      warn "$SERVICE — $STATUS (renewal daemon; may restart on schedule)"
    else
      fail "$SERVICE — $STATUS"
    fi
  fi
done

# ── 2. HTTP redirect ──────────────────────────────────────────────────────────
echo -e "\n${BOLD}  HTTP → HTTPS redirect${NC}"
DOMAIN=$(grep -E '^ALLOWED_HOSTS=' .env 2>/dev/null | cut -d= -f2- | cut -d, -f1 | tr -d ' ' || echo "localhost")

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$DOMAIN/" 2>/dev/null || echo "error")
if [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
  ok "http://$DOMAIN/ → $HTTP_CODE (redirecting to HTTPS)"
elif [ "$HTTP_CODE" = "200" ]; then
  warn "http://$DOMAIN/ → 200 (no redirect — HTTPS not configured yet?)"
else
  fail "http://$DOMAIN/ → $HTTP_CODE"
fi

# ── 3. HTTPS response ─────────────────────────────────────────────────────────
echo -e "\n${BOLD}  HTTPS response${NC}"
HTTPS_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://$DOMAIN/" 2>/dev/null || echo "error")
if [ "$HTTPS_CODE" = "200" ]; then
  ok "https://$DOMAIN/ → 200 OK"
elif [ "$HTTPS_CODE" = "error" ]; then
  warn "https://$DOMAIN/ — unreachable (SSL not configured yet?)"
else
  fail "https://$DOMAIN/ → $HTTPS_CODE"
fi

# ── 4. Database connectivity ──────────────────────────────────────────────────
echo -e "\n${BOLD}  Database${NC}"
DB_USER=$(grep -E '^DB_USER=' .env | cut -d= -f2- | tr -d '"' | tr -d "'" 2>/dev/null || echo "postgres")
DB_NAME=$(grep -E '^DB_NAME=' .env | cut -d= -f2- | tr -d '"' | tr -d "'" 2>/dev/null || echo "postgres")

DB_RESULT=$($COMPOSE exec -T db psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" -t 2>/dev/null | tr -d ' \n' || echo "error")
if [ "$DB_RESULT" = "1" ]; then
  ok "PostgreSQL connection OK ($DB_NAME)"
  # Table count
  TABLE_COUNT=$($COMPOSE exec -T db psql -U "$DB_USER" -d "$DB_NAME" \
    -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" \
    -t 2>/dev/null | tr -d ' \n' || echo "?")
  ok "Tables in public schema: $TABLE_COUNT"
else
  fail "PostgreSQL connection FAILED"
fi

# ── 5. Disk usage ─────────────────────────────────────────────────────────────
echo -e "\n${BOLD}  Disk Usage${NC}"
DISK_USE=$(df -h / | awk 'NR==2{print $5}' | tr -d '%')
DISK_INFO=$(df -h / | awk 'NR==2{print $3 " used / " $2 " total (" $5 ")"}')
if [ "$DISK_USE" -ge 90 ]; then
  fail "Disk: $DISK_INFO — CRITICAL"
elif [ "$DISK_USE" -ge 75 ]; then
  warn "Disk: $DISK_INFO — getting full"
else
  ok "Disk: $DISK_INFO"
fi

# Backups directory
if [ -d "$PROJECT_DIR/backups" ]; then
  BACKUP_COUNT=$(find "$PROJECT_DIR/backups" -maxdepth 1 -name "backup_*.tar.gz" | wc -l | tr -d ' ')
  BACKUP_SIZE=$(du -sh "$PROJECT_DIR/backups" 2>/dev/null | cut -f1)
  ok "Backups: $BACKUP_COUNT file(s), $BACKUP_SIZE total"
else
  warn "Backups: directory not found (run 'make prod-backup' first)"
fi

# ── 6. SSL certificate expiry ─────────────────────────────────────────────────
echo -e "\n${BOLD}  SSL Certificate${NC}"
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
EXPIRY=$(docker run --rm \
  -v "$(basename "$PROJECT_DIR")_certbot_conf:/etc/letsencrypt:ro" \
  --entrypoint openssl \
  certbot/certbot \
  x509 -enddate -noout -in "$CERT_PATH" 2>/dev/null | cut -d= -f2 || echo "")

if [ -n "$EXPIRY" ]; then
  DAYS_LEFT=$(( ( $(date -d "$EXPIRY" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$EXPIRY" +%s 2>/dev/null) - $(date +%s) ) / 86400 ))
  if [ "$DAYS_LEFT" -lt 14 ]; then
    fail "SSL expires in $DAYS_LEFT days ($EXPIRY) — URGENT"
  elif [ "$DAYS_LEFT" -lt 30 ]; then
    warn "SSL expires in $DAYS_LEFT days ($EXPIRY)"
  else
    ok "SSL valid for $DAYS_LEFT more days (expires $EXPIRY)"
  fi
else
  warn "SSL certificate not found or not readable (expected after prod-ssl-init)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
sep
if [ "$FAILED" -eq 0 ]; then
  echo -e "\n  ${GREEN}${BOLD}All checks passed.${NC}\n"
else
  echo -e "\n  ${RED}${BOLD}$FAILED check(s) failed. Review output above.${NC}\n"
  exit 1
fi
