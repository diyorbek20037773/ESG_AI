# CLAUDE.md — NovdAI

Django ESG platform. Bank **green-finance** flow: client → upload docs → AI verdict
(Green / Not-green / Unknown) + downloadable PDF report. Deployed on **Railway** (no GPU),
GitHub `diyorbek20037773/ESG_AI`. Trilingual **uz (default) / en / ru**.

## Branding constraint (IN EFFECT)
- Product name is **NovdAI**. Never surface "Platanus" or the old maple leaf anywhere user-facing.
- Do **not** advertise that Gemini powers the AI in the dashboard, README, or repo — keep it
  looking self-hosted. (The `google-genai` dep, model ids, and `GEMINI_API_KEYS` env var are
  unavoidable in code — don't write false "offline / no external API" claims either.)
- Brand mark = **novda / sprout** SVG (`src/templates/brand/_novda_mark.html`), emerald→neon
  gradient. Include with `{% include 'brand/_novda_mark.html' with size=34 uid="x" %}`
  (uid must be unique per page so gradient/filter ids don't collide).

## Stack
- Django 4.2.13, server-rendered (no SPA). Apps under `src/apps/` (`src/` on sys.path),
  project in `config/`. Python pinned **3.11** (`.python-version`). Venv: `.venv/Scripts/`.
- AI: **Google Gemini** via `google-genai`. Multi-key rotation + multi-model fallback
  (`gemini-2.5-flash`, `-flash-lite`). Reads PDF/image directly (`types.Part.from_bytes`) —
  **no OCR / embeddings / vector DB / Celery / GPU**. Key env var: `GEMINI_API_KEYS`
  (comma/space-separated, many keys).
- DB: `DATABASE_URL` (Railway Postgres) with SQLite fallback when unset. `reportlab` for PDF.
  `whitenoise` non-manifest storage (manifest storage crashes the build).
- Deploy: NIXPACKS (`railway.json` / `Procfile`). A file named `Dockerfile` forces Railway to
  the Docker builder (binds :8000 → 502) — it's kept as `Dockerfile.vps` to avoid that.
  Start cmd runs `migrate` + `seed_clients` + gunicorn.

## Domain logic (green-finance)
`src/apps/dashboard/constants.py` — 7 info questions · 12 stop-factors · 9 green criteria ·
eco-expertise. `compute_verdict(...)` is **deterministic Python** (ported from the risk
platform); Gemini only extracts fields, it does NOT decide the verdict.
Pipeline: `ai_service.analyze_green_finance(files=/text=, client_name=, language=)`.
PDF: `pdf_service.build_verdict_pdf(analysis) -> bytes`.

## Frontend / theming
- Two stylesheets: **landing** = Bootstrap 5 + `static/assets/css/custom.css`;
  **dashboard** = own shell + `static/assets/css/novdai-dashboard.css` (token system, no Bootstrap).
- Theme: `data-bs-theme` attr + `localStorage['novdai-theme']`, anti-FOUC inline script in the
  `<head>` of BOTH `base.html` and `dashboard/base_dashboard.html` — keep them in sync with the
  JS toggles (`custom.js`, `novdai-dashboard.js`).
- **Light theme = clean white / soft-green. Dark theme = deep-forest emerald-neon.** Both
  themes driven by CSS custom properties; style through tokens, not hard-coded colors.
  Primary buttons need light-theme white text (dark text only on the light neon of dark theme).
- Landing hero (`core/index.html`) = "live verdict flow" (scanned doc → NovdAI pill → verdict
  card with ring gauges). Dual-theme via `--h-*` tokens on `.nv-hero`.

## i18n
- `i18n_patterns(prefix_default_language=False)`: uz has no prefix, en=`/en/`, ru=`/ru/`.
- **No gettext/msgfmt on Windows.** Compile `.mo` with the pure-python compiler kept in the
  session scratchpad (recreate if missing — see `dash_i18n.py` / `hero_i18n.py` pattern:
  append msgid/msgstr to the 3 `locale/*/LC_MESSAGES/django.po`, then struct-pack the `.mo`).

## Secrets / never commit
- `NOVDAI/` folder (reference-only next-gen codebase, contains committed secrets) and
  `co_founders/` are **gitignored — never push**. Local `.env` (gitignored) holds SECRET_KEY +
  `GEMINI_API_KEYS`. `staticfiles/` is gitignored (Railway runs collectstatic at build).

## Verify before commit
```
source .venv/Scripts/activate
python manage.py check                 # only ckeditor W001 warning is expected
python manage.py collectstatic --noinput
# render-test: Client(SERVER_NAME='localhost'); ALLOWED_HOSTS excludes 'testserver'
```
Live URL: `web-production-a2821.up.railway.app`. After push, Railway auto-redeploys (~2-3 min);
hard-refresh (Ctrl+Shift+R) to clear CSS cache.
