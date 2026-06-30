#!/bin/bash
# =============================================================================
# backup.sh — Production backup: PostgreSQL + media files
#
# Usage:
#   bash scripts/backup.sh                  # full backup
#   BACKUP_KEEP_DAYS=14 bash scripts/backup.sh
#
# Output:
#   backups/YYYY-MM-DD_HH-MM-SS.tar.gz
#
# Backup includes:
#   - PostgreSQL full dump (gzip compressed)
#   - src/media/ directory (tar.gz)
#   - manifest.txt (metadata)
# =============================================================================
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUPS_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_NAME="backup_$TIMESTAMP"
BACKUP_WORK="$BACKUPS_DIR/$BACKUP_NAME"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${GREEN}[backup]${NC} $*"; }
warn() { echo -e "${YELLOW}[backup]${NC} $*"; }
err()  { echo -e "${RED}[backup] ERROR:${NC} $*" >&2; }

# ── Sanity checks ────────────────────────────────────────────────────────────
cd "$PROJECT_DIR"

if ! docker info >/dev/null 2>&1; then
  err "Docker is not running."; exit 1
fi

if [ ! -f ".env" ]; then
  err ".env file not found."; exit 1
fi

# Load DB credentials from .env (only the vars we need)
DB_NAME=$(grep -E '^DB_NAME=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
DB_USER=$(grep -E '^DB_USER=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
  err "DB_NAME or DB_USER not found in .env"; exit 1
fi

# Verify db container is running
if ! $COMPOSE ps db | grep -q "running\|Up"; then
  err "Database container is not running. Start services first."; exit 1
fi

# ── Create working directory ──────────────────────────────────────────────────
mkdir -p "$BACKUP_WORK"
info "Backup started: $BACKUP_NAME"

# ── 1. PostgreSQL dump ────────────────────────────────────────────────────────
info "Dumping PostgreSQL database '$DB_NAME' ..."
$COMPOSE exec -T db pg_dump \
  -U "$DB_USER" \
  --no-owner \
  --no-acl \
  --format=custom \
  "$DB_NAME" \
  | gzip > "$BACKUP_WORK/db.dump.gz"

DB_SIZE=$(du -sh "$BACKUP_WORK/db.dump.gz" | cut -f1)
info "  DB dump: $DB_SIZE"

# ── 2. Media files ────────────────────────────────────────────────────────────
MEDIA_DIR="$PROJECT_DIR/src/media"
if [ -d "$MEDIA_DIR" ] && [ "$(ls -A "$MEDIA_DIR" 2>/dev/null)" ]; then
  info "Archiving media files ..."
  tar -czf "$BACKUP_WORK/media.tar.gz" -C "$PROJECT_DIR/src" media
  MEDIA_SIZE=$(du -sh "$BACKUP_WORK/media.tar.gz" | cut -f1)
  info "  Media archive: $MEDIA_SIZE"
else
  warn "  Media directory is empty, skipping."
fi

# ── 3. Manifest ───────────────────────────────────────────────────────────────
cat > "$BACKUP_WORK/manifest.txt" <<EOF
Backup: $BACKUP_NAME
Date:   $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Commit: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
DB:     $DB_NAME (user: $DB_USER)
EOF

# ── 4. Compress everything into a single archive ──────────────────────────────
FINAL_ARCHIVE="$BACKUPS_DIR/${BACKUP_NAME}.tar.gz"
info "Compressing backup ..."
tar -czf "$FINAL_ARCHIVE" -C "$BACKUPS_DIR" "$BACKUP_NAME"
rm -rf "$BACKUP_WORK"   # remove uncompressed working dir

FINAL_SIZE=$(du -sh "$FINAL_ARCHIVE" | cut -f1)

# ── 5. Rotate old backups ─────────────────────────────────────────────────────
info "Removing backups older than ${BACKUP_KEEP_DAYS} days ..."
find "$BACKUPS_DIR" -maxdepth 1 -name "backup_*.tar.gz" \
  -mtime "+${BACKUP_KEEP_DAYS}" -exec rm -f {} \; -exec echo "  Deleted: {}" \;

BACKUP_COUNT=$(find "$BACKUPS_DIR" -maxdepth 1 -name "backup_*.tar.gz" | wc -l | tr -d ' ')

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Backup complete!${NC}"
echo -e "  File   : backups/${BACKUP_NAME}.tar.gz"
echo -e "  Size   : $FINAL_SIZE"
echo -e "  Stored : $BACKUP_COUNT backup(s) total"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
