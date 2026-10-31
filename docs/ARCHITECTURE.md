# Architecture

VenuePulse is a server-rendered Django application enhanced with HTMX (partial page updates) and Alpine.js (small,
local interactivity). There is no SPA and no JavaScript build step at runtime: CSS is compiled ahead of time and all
JavaScript is served from `venues/static/` — so the site works on any static-file setup and under a strict CSP.

## Django apps

| App | Responsibility | Key modules |
|---|---|---|
| `config` | Settings, URLs, cross-cutting middleware, ops endpoints | `settings/`, `middleware.py` (CSP + request IDs), `ratelimit.py`, `views.py` (`/healthz`, robots, manifest), `checks.py`, `forms.py` (form renderer) |
| `venues` | The catalogue: venues, subfield tags, deadline cycles, bookmarks | `models.py`, `filters.py` (all faceted filtering/sorting), `views.py` (HTML), `api.py` (JSON), `openapi.py`, `timeline.py`, `recommend.py`, `insights.py`, `seo.py`, `ics.py`, `serializers.py`, `management/commands/` |
| `accounts` | Profiles, auth flows, dashboard, notifications, saved searches, venue lists, private calendar feed | `views.py`, `forms.py`, `context_processors.py` (nav, canonical URL, CSP nonce) |
| `tracker` | Papers, submissions, checklists | `models.py` (`Submission.seed_checklist`), `views.py` |
| `community` | Experience reviews, deadline-change log, moderated corrections | `signals.py` (audit log), `admin.py` (approve action) |

## Data model (simplified)

```
ResearchSubfield ──< Venue >── DeadlineCycle (one per edition/year; UTC instants; AoE/UTC label;
                      │                       is_projected / verified_at / source_url)
                      ├──< VenueBookmark (user or anonymous key; starred + private note)
                      ├──< VenueReview (one per user)          DeadlineCycle ──< DeadlineChange (audit)
                      └──< Submission >── Paper                DeadlineCycle ──< DeadlineSuggestion
User ── UserProfile (timezone, interests, reminder offsets, digest opt-in, calendar & API tokens)
User ──< Notification · SavedSearch · VenueList (M2M Venue)
```

Deadline *status* (`open`, `upcoming`, `rolling`, `past`) and the *next deadline* are derived at read time from the
cycles, so they are always correct relative to "now". The same rules are expressed twice — as Python properties for
rendering and as `Exists`/`Subquery` filters in `venues/filters.py` — and the tests assert they agree.

## Request flow on the Explore page

1. `GET /` renders the full page (hero, sidebar facets, first page of results).
2. Changing any filter triggers `hx-get` from the sidebar form; the view detects `HX-Request` and returns only
   `partials/results.html`, which HTMX swaps into `#results` and pushes to history (`hx-push-url`).
3. `app.js` strips empty/default parameters in `htmx:configRequest`, so URLs stay short and shareable.
4. Server-sent events (`HX-Trigger: {"toast": …}`) drive toasts; countdowns tick from one shared Alpine clock store.

## Caching & performance

- Facet lists and insights aggregates are cached under a **catalogue version** key that is bumped by signals whenever a
  venue, cycle or tag changes — no stale caches, no manual invalidation.
- List views prefetch subfields and cycles and annotate tracker counts via subqueries; query-budget tests
  (`venues/tests_perf.py`) keep every hot page at a constant number of queries.
- JSON API responses carry weak ETags (catalogue version + hour bucket + query) and `Cache-Control`; HTML and JSON are
  gzip-compressed; static files are content-hashed and served with far-future caching by WhiteNoise.

## Security

- Production settings refuse to start without `DJANGO_SECRET_KEY`; HSTS (with preload), SSL redirect, secure cookies,
  `X-Frame-Options: DENY`, strict referrer policy, COOP and a `Permissions-Policy`.
- **Content-Security-Policy** with a per-request nonce for the single inline script (theme bootstrap). There are no
  inline event handlers; Alpine needs `'unsafe-eval'`, everything else is `'self'`.
- Cache-backed fixed-window **rate limiting** for login, signup, password reset, community writes, the public API and
  the token API, with standard `X-RateLimit-*`/`Retry-After` headers.
- Bearer API tokens and calendar tokens are random, revocable, and never shared with CORS-enabled endpoints.
- CSV exports neutralise spreadsheet formula injection; JSON-LD output is escaped like `json_script`.

## Front-end build

`npm run build` (Node 20+) runs three steps whose outputs are committed:

1. `frontend/vendor.mjs` — copies htmx, Alpine.js and Chart.js into `venues/static/venues/vendor/` (stripping
   source-map comments that would break `collectstatic`).
2. `frontend/build-icons.mjs` — scans templates for `{% icon "name" %}` and writes an SVG sprite with only those Lucide
   icons.
3. Tailwind compiles `frontend/styles.css` (design-system components such as `.btn-primary`, `.card`, `.input`) into
   `venues/static/venues/css/app.css`.

CI fails if the committed assets are out of date.

## Testing

- **Unit/integration** (`manage.py test`): ~200 tests across models, filters, views, API, commands, admin, security
  headers, rate limits, auth flows, settings (including a subprocess `check --deploy`), and query budgets. Runs on
  SQLite and PostgreSQL in CI with `-W error` locally.
- **End-to-end** (`npm run e2e`): Playwright drives a real server through filtering, view modes, starring, comparison,
  the command palette, theme persistence and kanban drag & drop, and runs axe-core WCAG 2.1 AA checks.
