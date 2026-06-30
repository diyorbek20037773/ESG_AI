#!/bin/bash
# =============================================================================
# update.sh — Zero-downtime production update
#
# Usage:
#   bash scripts/update.sh              # pulls current branch (default: main)
#   BRANCH=develop bash scripts/update.sh
#
# What it does:
#   1. git pull from the configured branch
#   2. Rebuild only the web image (db / nginx untouched)
#   3. Run the migrate one-shot service
#   4. Restart web with the new image
#   5. Verify health
# =============================================================================
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
BRANCH="${BRANCH:-main}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HEALTH_TIMEOUT=60   # seconds to wait for web to become healthy after restart

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[update]${NC} $*"; }
warn()    { echo -e "${YELLOW}[update]${NC} $*"; }
err()     { echo -e "${RED}[update] ERROR:${NC} $*" >&2; }

# ── Sanity checks ────────────────────────────────────────────────────────────
cd "$PROJECT_DIR"

if ! docker info >/dev/null 2>&1; then
  err "Docker is not running."
  exit 1
fi

if [ ! -f ".env" ]; then
  err ".env file not found. Copy .env.example and fill in the values."
  exit 1
fi

# Warn if there are local uncommitted changes (won't block the update)
if ! git diff --quiet || ! git diff --cached --quiet; then
  warn "You have uncommitted local changes. They will NOT be overwritten."
fi

# ── Step 1: Git pull ─────────────────────────────────────────────────────────
info "Fetching latest changes from origin/$BRANCH ..."
git fetch origin "$BRANCH"

LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  warn "Already up to date ($(git rev-parse --short HEAD)). Nothing to deploy."
  exit 0
fi

echo ""
info "Changes to be applied:"
git log --oneline "$LOCAL_SHA..$REMOTE_SHA"
echo ""

git pull origin "$BRANCH"
info "Pulled → $(git rev-parse --short HEAD)"

# ── Step 2: Rebuild web image ─────────────────────────────────────────────────
info "Building new web image ..."
$COMPOSE build web

# ── Step 3: Run migrations ────────────────────────────────────────────────────
# Remove any old migrate container so it can run fresh
info "Running database migrations ..."
$COMPOSE rm -f -s migrate 2>/dev/null || true
$COMPOSE run --rm --no-deps migrate

# ── Step 4: Restart web with new image ────────────────────────────────────────
# --no-deps keeps db and nginx running untouched
info "Restarting web service (nginx/db unaffected) ..."
$COMPOSE up -d --no-deps web

# ── Step 5: Wait for health check ─────────────────────────────────────────────
info "Waiting for web to become healthy (timeout: ${HEALTH_TIMEOUT}s) ..."
elapsed=0
until [ "$($COMPOSE ps -q web | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null)" = "healthy" ]; do
  if [ "$elapsed" -ge "$HEALTH_TIMEOUT" ]; then
    err "Web service did not become healthy in ${HEALTH_TIMEOUT}s."
    err "Run 'make prod-logs' to investigate."
    exit 1
  fi
  sleep 2
  elapsed=$((elapsed + 2))
done

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Deployment complete!${NC}"
echo -e "${GREEN}  Commit: $(git rev-parse --short HEAD)${NC}"
echo -e "${GREEN}  Branch: $BRANCH${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
$COMPOSE ps
