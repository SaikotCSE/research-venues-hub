# VenuePulse: Global Research Publication Venues & Deadlines Hub

Django 5 app for discovering, filtering, comparing and tracking conference / journal / workshop deadlines
with live countdowns (local time + AoE), ranks and formatting rules.

* **Stack:** Django 5.x (`config` project + `venues` app), SQLite by default / PostgreSQL-ready, Django Templates +
  HTMX + Alpine.js + Tailwind CSS + Lucide icons (via CDN), dark/light mode.
* **Data:** `python manage.py seed_venues` loads 110+ venues (AI/ML, medical imaging & bioinformatics, systems & security,
  SE/Web/HCI, multidisciplinary science) with 200+ deadline cycles. It is idempotent.

> Ranks, h5, impact factors and acceptance rates are approximate. Deadlines for future editions are **projections**
> extrapolated from earlier editions (shown as “Projected”). Always verify on the official site before submitting.

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_venues
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
python manage.py test              # 109 tests
python manage.py send_reminders    # run from cron / scheduler
```

PostgreSQL: `pip install "psycopg[binary]"` and set `DB_ENGINE=postgres DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT`.
Production: set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, run `collectstatic`.

## Feature tour

**Discover** – 113 seeded venues; instant HTMX filtering (type, domain, tags, CORE/CCF, quartile, impact factor, country,
continent, review model, open access, status); card / sortable table / 12‑month calendar views; side‑by‑side compare
(up to 4); live local + AoE countdowns; dark/light mode; `Ctrl/⌘+K` command palette.

**Plan** – *Recommender* (`/recommend/`): paste an abstract, get ranked venues with reasons. *Planner* (`/plan/`): "my paper
is ready on X" → deadlines you can still hit, with days of slack. *Insights* (`/insights/`): Chart.js dashboards.

**Track** (login) – Dashboard with next‑120‑day timeline; **submission tracker** kanban (planning → writing → submitted →
review → rebuttal → accepted/rejected) with auto‑generated, venue‑specific pre‑submission checklists; papers; starred
venues + notes (anonymous bookmarks merge into your account on login); custom **venue lists** (private or public share
links); **saved searches** with alerts.

**Stay informed** – `python manage.py send_reminders` (cron it) creates in‑app notifications + emails at your chosen
offsets (default 14/7/1 days), idempotently; private iCal subscription feed; filter‑based `/calendar.ics` and
`/feed/deadlines.atom`; per‑venue `.ics`.

**Community** – experience reviews (rating, review quality, turnaround, outcome) aggregated on each venue; date‑change
audit log ("deadline radar", `/community/changes/`); users can suggest corrections that admins approve in one click.

**Integrate** – public JSON API, bearer‑token API (`/api/v1/me/…`, docs at `/api/docs/`), CSV/JSON export honouring
filters. Admin for everything.

## Features / endpoints

| Path | Purpose |
|------|---------|
| `/` | Filterable list (HTMX, no reload): cards, sortable table, 12‑month calendar view |
| `/venue/<slug>/` (+ `/modal/`) | Detail page / quick-view modal: checklist, copy LaTeX/BibTeX, notes |
| `/venue/<slug>/ics/` | `.ics` download of all upcoming milestones |
| `/compare/?s=a&s=b` | Side-by-side comparison (up to 4; drawer in the UI) |
| `/targets/` | “My Target Venues” (per-user, or per-browser until you log in) |
| `/accounts/`, `/tracker/`, `/recommend/`, `/plan/`, `/insights/` | Dashboard, submission tracker, recommender, planner, charts |
| `/export/csv/`, `/export/json/` | Export, honouring all list filters; `?scope=targets` exports bookmarks |
| `/api/venues/`, `/api/venues/<slug>/`, `/api/tags/`, `/api/stats/` | JSON API |

Filter params (UI, API and exports): `q, type, domain, tag, core, ccf, quartile, min_if, country, continent, review, oa,
status (upcoming|open|rolling|past), sort (deadline|impact_factor|acceptance_rate|h5_index|rank|name), dir, view, page`.
