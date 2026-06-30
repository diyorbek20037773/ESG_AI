# Platanus — ESG AI Platform

A Django web platform combining a green-economy content site (news, blog, contact) with
an **ESG AI Dashboard**. The dashboard analyses company documents and text and produces
Environmental, Social and Governance scores, key findings, risks and recommendations.

The interface is fully localized in **English, Russian and Uzbek**.

## Features

- **ESG AI Dashboard** (`/dashboard/`)
  - Upload a company report (PDF / PNG / JPG / WEBP) or paste text.
  - Get E / S / G scores (0–100), an overall score with a letter rating, per-pillar
    summaries, key findings, risks and recommendations.
  - Analysis history with detail views.
- Multilingual UI (uz / en / ru) with a language switcher.
- News, blog and contact pages (CKEditor-powered content, model translations).
- Light / dark theme.

## Tech stack

- Django 4.2, PostgreSQL (SQLite fallback for local dev)
- `django-modeltranslation` for translatable content
- WhiteNoise for static files, Gunicorn for serving
- Bootstrap 5 + Tabler Icons frontend

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt

cp .env.example .env          # then edit .env
python manage.py migrate
python manage.py compilemessages   # optional; precompiled .mo files are committed
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the site and http://127.0.0.1:8000/dashboard/ for the
ESG dashboard.

### Environment variables

See `.env.example`. Key ones:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for local, `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `DATABASE_URL` | Postgres connection string (set automatically on Railway) |
| `GEMINI_API_KEYS` | One or more AI API keys, comma/space separated (used with rotation) |

## Deploy to Railway

1. Create a new Railway project from this GitHub repo.
2. Add a **PostgreSQL** plugin — Railway injects `DATABASE_URL` automatically.
3. Set environment variables: `SECRET_KEY`, `DEBUG=False`, and `GEMINI_API_KEYS`.
4. Railway builds with NIXPACKS and runs (from `railway.json`):

   ```
   python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT
   ```

`ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` pick up the Railway public domain automatically.

## Project layout

```
config/                 Django settings, urls, wsgi
src/apps/
  core/                 Home page + contact
  news/                 News
  blog/                 Blog
  users/                Auth
  dashboard/            ESG AI dashboard (analysis engine, models, views)
src/templates/          Templates (incl. dashboard/)
static/                 CSS, JS, images
locale/                 uz / en / ru translations
```
