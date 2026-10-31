# Architecture

VenuePulse is a **React + TypeScript single-page app** served by **Django**. Django owns the data, the JSON API, the
admin, emails, feeds and exports, and renders one small HTML shell per route with real titles, SEO metadata and the
data the first screen needs. React (built with Vite, styled with Tailwind CSS, interactive primitives from Radix UI)
renders everything the user sees and talks to Django over a session-authenticated JSON API.

The production bundle is built ahead of time and committed, so deploying needs no Node toolchain and the whole site
runs under a strict Content-Security-Policy (`script-src 'self'` plus one nonce'd theme snippet, no `unsafe-eval`).

## Django apps

| App | Responsibility | Key modules |
|---|---|---|
| `config` | Settings, URLs, cross-cutting middleware, ops endpoints | `settings/`, `middleware.py` (CSP + request IDs), `ratelimit.py`, `views.py` (`/healthz`, robots, manifest), `checks.py`, `site.py` |
| `webapp` | The app's server side: HTML shell, Vite manifest loader, session JSON API | `views.py` (shell + per-route metadata, 404s, CSRF failures), `vite.py`, `api/` (`session`, `catalog`, `account`, `tracker`, `community`), `serializers.py` |
| `venues` | The catalogue: venues, subfield tags, deadline cycles, bookmarks; public API, feeds, exports, widget | `models.py`, `filters.py` (faceted filtering/sorting), `services.py` (compare rows, calendar months, related venues), `api.py` (public JSON), `openapi.py`, `timeline.py`, `recommend.py`, `insights.py`, `seo.py`, `ics.py`, `views.py` (ICS/Atom/CSV/JSON/embed), `management/commands/` |
| `accounts` | Profiles, email verification, notifications, saved searches, venue lists, data export, private calendar feed | `models.py`, `forms.py`, `verification.py`, `views.py` (verify link, export, feeds), `signals.py` |
| `tracker` | Papers, submissions, checklists | `models.py` (`Submission.seed_checklist`), `forms.py` |
| `community` | Experience reviews, deadline-change log, moderated corrections | `signals.py` (audit log + notifications), `services.py` (review stats), `admin.py` (approve action) |

The forms in `accounts`, `tracker` and `community` are still the single place where input is validated; the JSON API
feeds request bodies into them and returns their errors per field.

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

When a cycle's dates change, `community/signals.py` writes a `DeadlineChange` audit row and notifies everyone who
starred the venue (if the change still matters, i.e. it touches a future date).

Deadline *status* (`open`, `upcoming`, `rolling`, `past`) and the *next deadline* are derived at read time from the
cycles, so they are always correct relative to "now". The same rules are expressed twice — as Python properties for
serialisation and as `Exists`/`Subquery` filters in `venues/filters.py` — and the tests assert they agree.

## How a page loads

1. Every route the React router knows is also a Django URL (keeping the historic URL names, so `reverse()`, emails,
   sitemaps and old links keep working). The view picks the HTTP status — 404 for an unknown venue or a private list,
   a redirect to the login page for signed-in-only pages — and renders `webapp/templates/webapp/shell.html`.
2. The shell carries the page title, description, canonical URL, Open Graph tags and, for venue pages, schema.org
   JSON-LD (`Event` or `Periodical` plus a `BreadcrumbList`). It also embeds **boot data** with `json_script`: the
   session (user, CSRF token, unread count, flash messages) and the API payload the first screen needs (facets, home
   stats and the first page of results on Explore; the full venue on a venue page).
3. `{% vite_assets %}` reads `.vite/manifest.json` and emits the stylesheet, `modulepreload` links for the entry's
   shared chunks **and for the current page's lazily-loaded chunk**, so everything downloads in parallel.
4. `main.tsx` seeds the TanStack Query cache from the boot data, waits until the router has loaded the page chunk,
   then renders once inside `startTransition` (time-sliced, so the main thread never blocks for long). Until then the
   server-rendered header stays on screen.
5. After that the app navigates client-side; data comes from `/api/app/…` and is cached per query key
   (`frontend/src/lib/query.ts`). Mutations update the cache optimistically (starring updates every cached list and the
   venue page at once) and roll back on errors.

## The app API (`/api/app/`)

- Session authentication with CSRF: the token comes from the boot data/`/session/` and is sent as `X-CSRFToken`.
  The client refreshes it and retries once if a CSRF check fails (e.g. after logging in in another tab).
- Request bodies are JSON objects; responses are JSON objects with `Cache-Control: private, no-store`.
- Errors are `{"error": "…", "fields": {"field": ["…"]}}` with 400/401/403/404/405/429 — including CSRF failures and
  unknown `/api/…` URLs, so the client never has to parse HTML.
- Endpoints are grouped by area: `session`/`auth/*`, catalogue (`facets`, `home`, `explore[/timeline|/calendar]`,
  `venues/<slug>/[star|note|review]`, `targets`, `compare`, `recommend`, `plan`, `radar`), the signed-in user
  (`me/*`, `lists/*`) and the tracker (`tracker/*`). Login, signup, password reset, email verification and community
  writes are rate limited.
- The password-reset link stores its token in the session and redirects to a `set-password` URL (like Django's own
  view), so the token never stays in the address bar or Referer.

The public, token-authenticated API (`/api/venues/`, `/api/v1/me/…`) is separate, versioned and documented with
OpenAPI; the app API is internal and may change with the frontend.

## Frontend

```
frontend/src/
  main.tsx, app.tsx      entry, router (every page lazy-loaded), providers
  pages/                 one module per route, exporting `Component` for React Router's `lazy`
  components/ui/         design-system primitives (shadcn-style wrappers around Radix: dialog, sheet, dropdown,
                         popover, select, tabs, tooltip, command, …) styled with Tailwind + CSS variables
  components/layout/     header, mobile menu, footer, command palette (loaded on first use), compare tray
  components/venue/      venue card, badges, countdowns, star/compare toggles, reviews, notes, lists, milestones
  components/explore/    filter panel, table/timeline/calendar views, export menu, saved searches, quick view
  providers/             session, theme, timezone, compare tray, command palette
  lib/                   API client, query keys & cache seeding, types mirroring the API, time maths, URL filters
```

- **Design tokens** live in `styles/index.css` as HSL CSS variables for light and dark themes (`--primary`,
  `--brand-text`, `--muted-foreground`, …), mapped to Tailwind colours in `tailwind.config.ts`. Colours were chosen to
  meet WCAG AA contrast; chart colours were validated for colour-vision deficiencies.
- **Time**: every instant is an ISO string in UTC. `lib/time.ts` formats it in the visitor's timezone (profile setting,
  last choice on this device, or the browser's) and in AoE. One shared clock drives all countdowns, and each countdown
  re-renders only when its visible text changes (once a minute for far-away deadlines).
- **Accessibility**: Radix primitives provide focus management and keyboard support; every control is labelled; the
  router moves focus to `<main>` on navigation; the kanban board supports keyboard drag & drop with screen-reader
  announcements plus a "Move to" menu; charts have a data-table view.
- **Performance**: route-level code splitting with server-side preloading; long-lived vendor chunks (`react`,
  `query`, `radix`, `icons`, `app`); off-screen cards use `content-visibility`; tooltips mount on first hover/focus.

## Caching & performance (server)

- Facet lists and insights aggregates are cached under a **catalogue version** key that is bumped by signals whenever a
  venue, cycle or tag changes — no stale caches, no manual invalidation.
- Querysets prefetch subfields and cycles and annotate tracker counts via subqueries; query-budget tests
  (`venues/tests_perf.py`) keep every hot endpoint at a constant number of queries.
- Public API responses carry weak ETags and `Cache-Control`; HTML and JSON are gzip-compressed; Vite's content-hashed
  assets are served by WhiteNoise with `Cache-Control: immutable` (`WHITENOISE_IMMUTABLE_FILE_TEST`).

## Security

- Production settings refuse to start without `DJANGO_SECRET_KEY`; HSTS (with preload), SSL redirect, secure cookies,
  `X-Frame-Options: DENY`, strict referrer policy, COOP and a `Permissions-Policy`.
- **Content-Security-Policy**: `script-src 'self'` plus a per-request nonce for the theme bootstrap snippet; JSON boot
  data and JSON-LD are non-executable data blocks escaped like `json_script`. No inline event handlers, no CDNs.
- Cache-backed fixed-window **rate limiting** for login, signup, password reset, email verification, community writes,
  the public API and the token API, with `X-RateLimit-*`/`Retry-After` headers.
- Bearer API tokens and calendar tokens are random, revocable, and never sent to CORS-enabled endpoints.
- Email verification uses Django's signing framework: tokens are bound to the user *and* the address, expire after three
  days, and need no database table. Reminder and digest emails are sent only to confirmed addresses.
- The embeddable widget (`/embed/venue/<slug>/`) is the only frameable page: it keeps the same CSP but relaxes
  `frame-ancestors` and is exempt from `X-Frame-Options`.
- CSV exports neutralise spreadsheet formula injection.

## Build

`npm run build` type-checks the app and runs Vite, which writes the bundle and `.vite/manifest.json` to
`webapp/static/webapp/` (committed). Django references the hashed files directly under `STATIC_URL` instead of
hashing them again, so chunks can import each other by their Vite names. CI fails if the committed bundle is stale.

For development, `npm run dev` serves modules with hot reloading; set `VITE_DEV_SERVER_URL=http://localhost:5173` and
Django's shell loads the app from Vite instead (local settings widen the CSP for the dev server).

## Testing

- **Django** (`manage.py test`, warnings as errors): ~215 tests across models, filters, the app API and the shell,
  the public API, commands, admin, security headers, CSP, CSRF, rate limits, auth flows, settings (including a
  subprocess `check --deploy`) and query budgets. Runs on SQLite and PostgreSQL in CI.
- **Frontend unit tests** (`npm test`, Vitest + Testing Library): time maths, URL filter helpers, the API client
  (CSRF header, error mapping, retry), form-field accessibility wiring.
- **End-to-end** (`npm run e2e`, Playwright): filtering and views, the command palette, starring/notes/comparison as an
  anonymous visitor, sign-up with star merging, login redirects, the tracker (create → checklist → move), lists,
  reviews, settings, theme persistence, axe-core WCAG 2.1 AA checks on key pages, and a mobile overflow check.
