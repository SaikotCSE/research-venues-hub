# VenuePulse — Research Venues & Deadlines Hub

**Never miss a submission deadline.** VenuePulse is a Django 5 web app for researchers to discover, compare and track
conferences, journals and symposia — with live countdowns in your own timezone *and* Anywhere-on-Earth, ranks and
metrics, formatting rules, a submission tracker, reminders, calendar feeds and a public JSON API.

![Explore page](docs/screenshots/explore.jpg)

<table>
<tr>
<td><img src="docs/screenshots/timeline.jpg" alt="Timeline (Gantt) view"></td>
<td><img src="docs/screenshots/venue-detail-dark.jpg" alt="Venue detail page in dark mode"></td>
</tr>
<tr>
<td><img src="docs/screenshots/tracker.jpg" alt="Submission tracker kanban board"></td>
<td><img src="docs/screenshots/compare-drawer.jpg" alt="Side-by-side comparison drawer"></td>
</tr>
</table>

> Ranks, h5-indices, impact factors and acceptance rates in the seed data are approximate. Deadlines for future
> editions are **projections** from previous editions and are labelled *Projected* until an editor verifies them.
> Always confirm on the official venue website before submitting.

---

## Features

**Discover**
- 113 seeded venues (AI/ML, NLP, vision, medical imaging & bioinformatics, systems, security, databases, SE, HCI, web,
  multidisciplinary science) with 230+ deadline cycles.
- Instant HTMX filtering — type, domain, subfield tags, CORE/CCF rank, journal quartile, impact factor, country/continent,
  review model, open access, deadline status and *closing within N days* — with removable filter chips and clean,
  shareable URLs.
- Four views: **cards**, sortable **table**, Gantt-style **timeline** (call → review → camera-ready → event), and a
  12-month **calendar**.
- Live countdowns in your chosen timezone and AoE; a *closing soon* panel; side-by-side **comparison** of up to four
  venues with best values highlighted.
- Venue pages with a milestone stepper, all past/future cycles, submission & formatting checklist, official LaTeX
  preambles and BibTeX templates (one-click copy), Google/Outlook/.ics calendar links, related venues, community
  experience reports and a data-quality panel.
- **Recommender** (paste an abstract → ranked venues with reasons), **deadline planner** (ready date → deadlines you can
  still make, with slack), **insights** dashboards, and a **deadline radar** of date changes.
- Command palette (<kbd>Ctrl</kbd>/<kbd>⌘</kbd>+<kbd>K</kbd>), keyboard shortcuts (<kbd>?</kbd>), light/dark/system
  theme, mobile-friendly layout, print styles.

**Track** (free account)
- Dashboard with onboarding checklist, upcoming deadlines, active submissions, notifications and recommendations.
- **Submission tracker** kanban (planning → writing → submitted → review → rebuttal → accepted/rejected) with drag &
  drop and auto-generated, venue-specific checklists; papers can be resubmitted to several venues.
- Starred venues with private notes (anonymous stars merge into your account when you sign up), shareable **venue
  lists**, **saved searches** with alerts.
- Reminders at your chosen offsets (default 14/7/1 days), a **weekly digest email**, and a private iCal subscription.
- Account settings: email change, password change/reset, **JSON export of all your data**, account deletion.

**Integrate**
- Public JSON API with pagination links, ETags/`304`, CORS and rate-limit headers; bearer-token API for your own
  targets and submissions; [OpenAPI 3.1 schema](venues/openapi.py) and an interactive docs page at `/api/docs/`.
- CSV/JSON exports, filter-driven `.ics` and Atom feeds, `import_venues` to load or update data from CSV/JSON.

**Operate**
- Secure-by-default production settings (HSTS, secure cookies, nonce-based CSP, Permissions-Policy, rate limiting),
  `/healthz`, structured logs with request IDs, sitemap, robots.txt, web manifest, custom error pages.
- Dockerfile (non-root, healthcheck), docker-compose (PostgreSQL + Redis + scheduler), gunicorn, Procfile.
- CI: ruff, 200 Django tests on Python 3.12/3.13 × SQLite/PostgreSQL (≈95 % coverage), deploy checks, asset
  freshness, Docker smoke test, Playwright end-to-end + axe accessibility tests.

## Quick start

Requirements: Python 3.12+ (Node 20+ only if you change templates/CSS).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_venues            # the venue catalogue (idempotent)
python manage.py seed_demo              # optional: demo account, prints its password
python manage.py createsuperuser        # optional: for /admin/
python manage.py runserver
```

Open <http://localhost:8000>. Copy `.env.example` to `.env` to configure anything (the defaults work for development).

Or run the production-like stack (gunicorn + PostgreSQL + Redis + reminder scheduler):

```bash
cp .env.example .env   # set DJANGO_SECRET_KEY; for plain-HTTP localhost also set the three "local docker" lines
docker compose up --build
```

## Everyday commands

| Command | What it does |
|---|---|
| `make test` / `python -W error manage.py test` | Django test-suite (uses `config.settings.test` automatically) |
| `make coverage` | Tests with a coverage report |
| `make lint` / `make format` | Ruff lint + format check / auto-fix |
| `make check` | System checks, migration check, and `check --deploy` against production settings |
| `npm ci && npm run build` | Rebuild compiled CSS, icon sprite and vendored JS (commit the output) |
| `npm run e2e` | Playwright browser tests + axe accessibility checks (starts its own server) |
| `python manage.py send_reminders` | Deadline reminders & saved-search alerts (run hourly) |
| `python manage.py send_digest --if-due` | Weekly digest email (safe to run hourly) |
| `python manage.py import_venues file.json --dry-run` | Validate/import venues from CSV or JSON (export format) |

## Project layout

```
config/       settings (base/local/test/production), middleware (CSP, request IDs), rate limiter, ops views, checks
venues/       catalogue models, filters, views, JSON API, OpenAPI, timeline/recommender/insights, seed data, commands
accounts/     profiles, auth flows, dashboard, notifications, saved searches, venue lists, calendar feed
tracker/      papers, submissions kanban, checklists
community/    experience reviews, deadline-change audit log, moderated corrections
frontend/     Tailwind input CSS, icon-sprite and vendoring scripts
templates/    project-wide templates: error pages and the form renderer
e2e/          Playwright end-to-end tests
docs/         architecture, deployment notes, screenshots
```

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) ·
[CONTRIBUTING.md](CONTRIBUTING.md) · [CHANGELOG.md](CHANGELOG.md)

## Configuration

All settings come from environment variables (or `.env`); see [`.env.example`](.env.example). The most important:

| Variable | Default | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev key in local settings | **Required** in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated |
| `SITE_URL` | request host | Public base URL used in emails, feeds and canonical links |
| `DATABASE_URL` | SQLite `db.sqlite3` | e.g. `postgres://user:pass@host:5432/venuepulse` |
| `REDIS_URL` | — | Enables the Redis cache (shared rate limits & caches across workers) |
| `EMAIL_HOST` … | console backend | SMTP settings for reminders, digests and password resets |
| `DJANGO_ADMIN_URL` | `admin/` | Move the admin in production |
| `CSP_REPORT_ONLY` | `0` | Report-only mode while rolling out CSP changes |
