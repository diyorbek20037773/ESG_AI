#!/bin/sh
set -e

# ─── Wait for PostgreSQL (only for a real external DB) ─────────────────────────
# On Railway the DB is reached via DATABASE_URL and is immediately available, so
# we skip the wait there. We only wait when an explicit, non-local DB_HOST is set
# (e.g. docker-compose's "db" service). The wait is non-fatal: if it times out we
# still continue and let Django report a clear error.
if [ -n "$DB_HOST" ] && [ "$DB_HOST" != "localhost" ] && [ "$DB_HOST" != "127.0.0.1" ] && [ -z "$DATABASE_URL" ]; then
  DB_PORT="${DB_PORT:-5432}"
  DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-60}"
  echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} (timeout: ${DB_WAIT_TIMEOUT}s) ..."
  elapsed=0
  until nc -z "$DB_HOST" "$DB_PORT"; do
    if [ "$elapsed" -ge "$DB_WAIT_TIMEOUT" ]; then
      echo "[entrypoint] WARNING: PostgreSQL not ready in ${DB_WAIT_TIMEOUT}s, continuing anyway."
      break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
fi

# ─── Django setup ─────────────────────────────────────────────────────────────
if [ "${SKIP_MIGRATE:-false}" != "true" ]; then
  echo "[entrypoint] Running migrations ..."
  python manage.py migrate --noinput
fi

echo "[entrypoint] Collecting static files ..."
python manage.py collectstatic --noinput

# ─── Start Gunicorn (bind to Railway's $PORT, fall back to 8000 locally) ───────
PORT="${PORT:-8000}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Platanus running → 0.0.0.0:${PORT}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --worker-tmp-dir /dev/shm \
    ${GUNICORN_RELOAD:+--reload} \
    --timeout "${GUNICORN_TIMEOUT:-180}" \
    --access-logfile - \
    --error-logfile - \
    --log-level info
