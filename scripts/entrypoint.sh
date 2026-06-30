#!/bin/sh
set -e

# ─── Wait for PostgreSQL ───────────────────────────────────────────────────────
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-60}"   # max seconds to wait

echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} (timeout: ${DB_WAIT_TIMEOUT}s) ..."
elapsed=0
until nc -z "$DB_HOST" "$DB_PORT"; do
  if [ "$elapsed" -ge "$DB_WAIT_TIMEOUT" ]; then
    echo "[entrypoint] ERROR: PostgreSQL did not become ready in ${DB_WAIT_TIMEOUT}s. Aborting."
    exit 1
  fi
  sleep 1
  elapsed=$((elapsed + 1))
done
echo "[entrypoint] PostgreSQL is ready."

# ─── Django setup ─────────────────────────────────────────────────────────────
# SKIP_MIGRATE=true is set by docker-compose.prod.yml because a dedicated
# 'migrate' service already ran migrations before this container started.
if [ "${SKIP_MIGRATE:-false}" != "true" ]; then
  echo "[entrypoint] Running migrations ..."
  python manage.py migrate --noinput
fi

echo "[entrypoint] Collecting static files ..."
# No --clear: avoids a brief window where static files are absent during restart.
# Stale files are harmless for a landing-page deployment.
python manage.py collectstatic --noinput

# ─── Start Gunicorn ───────────────────────────────────────────────────────────
WORKERS="${GUNICORN_WORKERS:-3}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Platanus running → http://localhost:8000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$WORKERS" \
    --worker-tmp-dir /dev/shm \
    ${GUNICORN_RELOAD:+--reload} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
