# VenuePulse — Research Venues & Deadlines Hub

**Never miss a submission deadline.** VenuePulse helps researchers discover, compare and track conferences, journals
and symposia — with live countdowns in your own timezone *and* Anywhere-on-Earth, ranks and metrics, formatting rules,
a submission tracker, reminders, calendar feeds and a public JSON API.

It is a **React + TypeScript** single-page app (Vite, Tailwind CSS, Radix UI primitives) on a **Django 5** backend that
serves a JSON API, server-rendered SEO metadata, the admin, emails, feeds and exports.

![Explore page](docs/screenshots/explore.jpg)

<table>
<tr>
<td><img src="docs/screenshots/venue-detail-dark.jpg" alt="Venue page in dark mode"></td>
<td><img src="docs/screenshots/timeline.jpg" alt="Timeline (Gantt) view of deadlines"></td>
</tr>
<tr>
<td><img src="docs/screenshots/tracker.jpg" alt="Submission tracker kanban board"></td>
<td><img src="docs/screenshots/compare.jpg" alt="Side-by-side venue comparison"></td>
</tr>
<tr>
<td><img src="docs/screenshots/dashboard.jpg" alt="Personal dashboard"></td>
<td><img src="docs/screenshots/insights-dark.jpg" alt="Insights charts in dark mode"></td>
</tr>
</table>

> Ranks, h5-indices, impact factors and acceptance rates in the seed data are approximate. Deadlines for future
> editions are **projections** from previous editions and are labelled *Projected* until an editor verifies them.
> Always confirm on the official venue website before submitting.

---

## Features

**Discover**
- 136 seeded venues (AI/ML, NLP, vision, medical imaging & bioinformatics, systems, security, databases, SE, HCI, web,
  multidisciplinary science) with 250+ deadline cycles.
- Instant filtering — type, domain, topics, CORE/CCF rank, journal quartile, minimum impact factor, country/continent,
  review model, open access, deadline status and *closing within N days* — with removable chips and shareable URLs.
- Four views: **cards**, sortable **table**, Gantt-style **timeline** (call → review → camera-ready → event) and a
  12-month **calendar**; a *closing soon* strip and catalogue stats on the home page.
- Live countdowns in your chosen timezone with the AoE time on hover; **quick view** dialogs; side-by-side
  **comparison** of up to four venues with the best values highlighted.
- Venue pages with a live countdown, milestone stepper, submission-window progress, every edition's dates, submission
  checklist, official LaTeX preambles and BibTeX entries (one-click copy), Google/Outlook/.ics calendar links, related
  venues, community experience reviews, deadline-change history and correction suggestions.
- **Recommender** (paste an abstract → ranked venues with reasons), **deadline planner** (ready date → venues you can
  still make, with slack), **insights** charts and a public **deadline radar**.
- Command palette (<kbd>Ctrl</kbd>/<kbd>⌘</kbd>+<kbd>K</kbd> or <kbd>/</kbd>) with venue search, pages, actions and
  recently viewed venues; light/dark/system theme; fully responsive layout.
- **Embeddable countdown widget** (`/embed/venue/<slug>/`, light or dark) for lab and course websites.

**Track** (free account)
- Dashboard with onboarding checklist, the next 120 days of deadlines, active submissions, notifications, saved
  searches, recommendations for your interests and your private calendar feed.
- **Submission tracker** kanban (planning → writing → submitted → review → rebuttal → accepted/rejected) with
  keyboard-accessible drag & drop, a "Move to" menu and auto-generated, venue-specific checklists.
- Starred venues with private notes (anonymous stars merge into your account when you sign up), shareable **venue
  lists** with their own calendar feeds, **saved searches** with alerts.
- Reminders at your chosen offsets (default 14/7/1 days), a **weekly digest email**, a private iCal subscription and
  **notifications when a tracked deadline moves**. Emails go only to confirmed addresses.
- Account settings: email change, password change/reset, **JSON export of all your data**, account deletion.

**Integrate**
- Public JSON API with pagination links, ETags/`304`, CORS and rate-limit headers; bearer-token API for your own
  targets and submissions; [OpenAPI 3.1 schema](venues/openapi.py) and interactive docs with a live console at
  `/api/docs/`.
- CSV/JSON exports, filter-driven `.ics` and Atom feeds, `import_venues` to load or update data from CSV/JSON.

**Operate**
- Secure-by-default production settings (HSTS, secure cookies, strict nonce-based CSP with no `unsafe-eval`,
  Permissions-Policy, rate limiting), `/healthz`, request-ID logging, sitemap, robots.txt, web manifest.
- Dockerfile (non-root, healthcheck, no Node needed — the bundle is committed), docker-compose (PostgreSQL + Redis +
  scheduler), gunicorn, Procfile.
- CI: ruff; 210+ Django tests on Python 3.12/3.13 × SQLite/PostgreSQL (≈95 % coverage); deploy checks; TypeScript,
  ESLint, Prettier and Vitest for the frontend; bundle freshness; Docker smoke test; Playwright end-to-end tests with
  axe-core accessibility checks and a mobile overflow check.
- Quality bar: zero serious axe-core WCAG 2.1 AA violations; Lighthouse (mobile emulation, production settings) scores
  100 for accessibility, best practices and SEO and ~90 for performance on the home and venue pages.

## Quick start

Requirements: Python 3.12+. Node 20+ only if you change the frontend (the built bundle is committed).

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

Working on the frontend? Run Vite with hot reloading next to Django:

```bash
npm ci
npm run dev                                                   # Vite on :5173
VITE_DEV_SERVER_URL=http://localhost:5173 python manage.py runserver   # pages load modules from Vite
# or simply: make web
```

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
| `npm run typecheck` · `npm run lint` · `npm test` | TypeScript, ESLint and Vitest for the React app (`make test-web`) |
| `npm run build` | Build the React bundle into `webapp/static/webapp/` (commit the output) |
| `npm run e2e` | Playwright browser tests + axe accessibility checks (starts its own server) |
| `python manage.py send_reminders` | Deadline reminders & saved-search alerts (run hourly) |
| `python manage.py send_digest --if-due` | Weekly digest email (safe to run hourly) |
| `python manage.py import_venues file.json --dry-run` | Validate/import venues from CSV or JSON (export format) |

## Project layout

```
frontend/src/  React app: pages/, components/ (ui primitives, layout, venue, explore), providers/, lib/ (API client,
               types, time maths), hooks/, styles/ (Tailwind + design tokens)
webapp/        Django side of the app: HTML shell with per-route SEO + boot data, Vite manifest loader,
               session-authenticated JSON API (api/), committed production bundle (static/webapp/)
config/        settings (base/local/test/production), middleware (CSP, request IDs), rate limiter, ops views, checks
venues/        catalogue models, filters, public JSON API, OpenAPI, timeline/recommender/insights, feeds, exports,
               embed widget, seed data, management commands
accounts/      profiles, email verification, notifications, saved searches, venue lists, data export, calendar feed
tracker/       papers, submissions, checklists
community/     experience reviews, deadline-change audit log, moderated corrections
templates/     server error pages
e2e/           Playwright end-to-end tests
docs/          architecture, deployment notes, screenshots
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
| `VITE_DEV_SERVER_URL` | — | Development only: load the app from `npm run dev` for hot reloading |
