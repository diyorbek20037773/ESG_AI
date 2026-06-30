#!/bin/bash
# =============================================================================
# restore.sh — Restore PostgreSQL + media from a backup archive
#
# Usage:
#   bash scripts/restore.sh                          # interactive: pick backup
#   bash scripts/restore.sh backup_2026-01-15_12-00-00.tar.gz
#
# WARNING: This OVERWRITES the current database and media files.
#          A safety backup is taken automatically before restore begins.
# =============================================================================
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUPS_DIR="$PROJECT_DIR/backups"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[restore]${NC} $*"; }
warn()    { echo -e "${YELLOW}[restore]${NC} $*"; }
err()     { echo -e "${RED}[restore] ERROR:${NC} $*" >&2; }
heading() { echo -e "${CYAN}$*${NC}"; }

# ── Sanity checks ─────────────────────────────────────────────────────────────
cd "$PROJECT_DIR"

if ! docker info >/dev/null 2>&1; then err "Docker is not running."; exit 1; fi
if [ ! -f ".env" ]; then err ".env file not found."; exit 1; fi

DB_NAME=$(grep -E '^DB_NAME=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
DB_USER=$(grep -E '^DB_USER=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
  err "DB_NAME or DB_USER not found in .env"; exit 1
fi

# ── Select backup ─────────────────────────────────────────────────────────────
SELECTED_ARCHIVE=""

if [ "${1:-}" != "" ]; then
  # Archive name passed as argument
  if [ -f "$BACKUPS_DIR/$1" ]; then
    SELECTED_ARCHIVE="$BACKUPS_DIR/$1"
  elif [ -f "$1" ]; then
    SELECTED_ARCHIVE="$1"
  else
    err "Backup file not found: $1"; exit 1
  fi
else
  # Interactive selection
  mapfile -t ARCHIVES < <(find "$BACKUPS_DIR" -maxdepth 1 -name "backup_*.tar.gz" | sort -r)

  if [ ${#ARCHIVES[@]} -eq 0 ]; then
    err "No backups found in $BACKUPS_DIR"; exit 1
  fi

  heading ""
  heading "  Available backups:"
  heading "  ─────────────────────────────────────────"
  for i in "${!ARCHIVES[@]}"; do
    SIZE=$(du -sh "${ARCHIVES[$i]}" | cut -f1)
    echo "  [$((i+1))] $(basename "${ARCHIVES[$i]}")  ($SIZE)"
  done
  heading "  ─────────────────────────────────────────"
  echo ""

  read -rp "  Enter number [1-${#ARCHIVES[@]}]: " CHOICE
  if ! [[ "$CHOICE" =~ ^[0-9]+$ ]] || [ "$CHOICE" -lt 1 ] || [ "$CHOICE" -gt "${#ARCHIVES[@]}" ]; then
    err "Invalid selection."; exit 1
  fi

  SELECTED_ARCHIVE="${ARCHIVES[$((CHOICE-1))]}"
fi

ARCHIVE_NAME=$(basename "$SELECTED_ARCHIVE")
info "Selected: $ARCHIVE_NAME"

# ── Confirmation ──────────────────────────────────────────────────────────────
echo ""
warn "This will OVERWRITE the current database '$DB_NAME' and media files."
warn "A pre-restore safety backup will be created first."
echo ""
read -rp "  Type 'yes' to proceed: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  info "Restore cancelled."; exit 0
fi
echo ""

# ── Pre-restore safety backup ────────────────────────────────────────────────
info "Creating pre-restore safety backup ..."
bash "$(dirname "$0")/backup.sh"

# ── Extract archive ───────────────────────────────────────────────────────────
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

info "Extracting archive ..."
tar -xzf "$SELECTED_ARCHIVE" -C "$WORK_DIR"
BACKUP_DIR="$WORK_DIR/$(ls "$WORK_DIR")"

# Show manifest
if [ -f "$BACKUP_DIR/manifest.txt" ]; then
  echo ""
  cat "$BACKUP_DIR/manifest.txt"
  echo ""
fi

# ── Stop web (DB must be idle during restore) ─────────────────────────────────
info "Pausing web service ..."
$COMPOSE stop web 2>/dev/null || true

# ── Restore database ──────────────────────────────────────────────────────────
if [ -f "$BACKUP_DIR/db.dump.gz" ]; then
  info "Restoring PostgreSQL database '$DB_NAME' ..."

  # Drop all connections and recreate the DB cleanly
  $COMPOSE exec -T db psql -U "$DB_USER" -d postgres <<SQL
SELECT pg_terminate_backend(pid)
FROM   pg_stat_activity
WHERE  datname = '$DB_NAME' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$DB_NAME";
CREATE DATABASE "$DB_NAME" OWNER "$DB_USER";
SQL

  # Restore from custom-format dump
  gunzip -c "$BACKUP_DIR/db.dump.gz" \
    | $COMPOSE exec -T db pg_restore \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-acl \
        --exit-on-error

  info "  Database restored."
else
  warn "  No db.dump.gz found in archive, skipping DB restore."
fi

# ── Restore media files ───────────────────────────────────────────────────────
if [ -f "$BACKUP_DIR/media.tar.gz" ]; then
  info "Restoring media files ..."
  rm -rf "$PROJECT_DIR/src/media"
  tar -xzf "$BACKUP_DIR/media.tar.gz" -C "$PROJECT_DIR/src"
  info "  Media files restored."
else
  warn "  No media.tar.gz found in archive, skipping media restore."
fi

# ── Restart web ───────────────────────────────────────────────────────────────
info "Restarting web service ..."
$COMPOSE up -d --no-deps web

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Restore complete!${NC}"
echo -e "  From: $ARCHIVE_NAME"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
