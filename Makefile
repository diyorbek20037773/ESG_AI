.PHONY: build up down logs shell migrate superuser \
        prod-up prod-down prod-logs prod-shell \
        prod-migrate prod-superuser prod-restart prod-collectstatic \
        prod-ssl-init prod-reload-nginx \
        prod-update prod-backup prod-restore prod-health

LOCAL  := docker compose -f docker-compose.yml -f docker-compose.local.yml
PROD   := docker compose -f docker-compose.yml -f docker-compose.prod.yml

# ─── Docker — local development ───────────────────────────────────────────────
build:
	$(LOCAL) build

up:
	$(LOCAL) up --build

down:
	$(LOCAL) down

logs:
	$(LOCAL) logs -f web

shell:
	$(LOCAL) exec web python manage.py shell

migrate:
	$(LOCAL) exec web python manage.py migrate

superuser:
	$(LOCAL) exec web python manage.py createsuperuser

# ─── Docker — production ──────────────────────────────────────────────────────
prod-up:
	$(PROD) up -d --build

prod-down:
	$(PROD) down

prod-logs:
	$(PROD) logs -f web

prod-shell:
	$(PROD) exec web python manage.py shell

prod-migrate:
	$(PROD) exec web python manage.py migrate

prod-superuser:
	$(PROD) exec web python manage.py createsuperuser

prod-collectstatic:
	$(PROD) exec web python manage.py collectstatic --noinput

prod-restart:
	$(PROD) restart web nginx

# ── First-time SSL setup (run ONCE on a fresh server) ─────────────────────────
# Usage: CERTBOT_EMAIL=you@email.com make prod-ssl-init
# Optional: STAGING=1 make prod-ssl-init  (test without rate-limit)
prod-ssl-init:
	@bash scripts/init-letsencrypt.sh

# Graceful nginx config reload (no downtime)
prod-reload-nginx:
	$(PROD) exec nginx nginx -s reload

# ── Server management ─────────────────────────────────────────────────────────
# Pull latest git changes, rebuild web image, run migrations, restart web
prod-update:
	@bash scripts/update.sh

# Full backup: PostgreSQL dump + media files → backups/
# Optional: BACKUP_KEEP_DAYS=14 make prod-backup
prod-backup:
	@bash scripts/backup.sh

# Restore from a backup (interactive if no argument given)
# Usage: make prod-restore                          (interactive)
#        make prod-restore FILE=backup_2026-01-01_12-00-00.tar.gz
prod-restore:
	@bash scripts/restore.sh $(FILE)

# Show health of all services, SSL cert, disk, DB
prod-health:
	@bash scripts/health-check.sh
