# Changelog

All notable changes to this project are documented here. Dates are in UTC.

## [2.0.0] — 2026-10-31

### Changed
- **New frontend:** the HTMX/Alpine templates are replaced by a React 18 + TypeScript single-page app built with Vite,
  Tailwind CSS and Radix UI primitives (shadcn-style component library, Inter typeface, lucide icons). New visual
  design throughout with refined light and dark themes.
- Django now serves an HTML shell per route (titles, canonical URLs, Open Graph, JSON-LD, correct 404s and login
  redirects) with the first screen's data embedded, plus a session-authenticated JSON API under `/api/app/` that
  reuses the existing forms for validation. All existing URLs and URL names keep working.
- Content-Security-Policy no longer needs `'unsafe-eval'`.

### Added
- Command palette with live venue search, recent venues, pages and actions; quick-view dialogs on venue cards;
  comparison tray; keyboard-accessible kanban drag & drop with screen-reader announcements and a "Move to" menu.
- Venue pages: segmented live countdown, submission-window progress, milestone stepper, tabbed LaTeX/BibTeX snippets,
  inline lists membership, review dialog with star ratings, correction-suggestion dialog, embed & API panel.
- Insights rebuilt with Recharts, each chart with a data-table view; colour palette validated for colour-vision
  deficiencies.
- Notifications popover, onboarding progress, saved-search dialog, data-export and account-deletion dialogs,
  password visibility toggles, optimistic updates for stars, notes, checklists and board moves.
- Frontend tooling: TypeScript strict mode, ESLint (with jsx-a11y and React Hooks rules), Prettier, Vitest + Testing
  Library unit tests; new Playwright suite covering anonymous, sign-up and signed-in flows with axe-core checks.
- Performance: route-level code splitting with server-side preloading of the current page's chunk, time-sliced first
  render, shared countdown clock, lazily mounted tooltips and command palette, `content-visibility` for off-screen
  cards, immutable caching for hashed assets.

### Removed
- HTMX, Alpine.js and Chart.js, the server-rendered page templates, the icon sprite and the template form renderer.

## [1.0.0] — 2026-10-31

### Added
- **Front-end:** compiled Tailwind design system, self-hosted htmx/Alpine/Chart.js, Lucide SVG sprite with an
  `{% icon %}` tag; light/dark/system theme; timezone picker; command palette; keyboard shortcuts; toasts; skip link;
  accessible dialogs; print styles; web manifest and app icons.
- **Explore:** removable filter chips, "closing within N days" filter, Gantt-style timeline view, closing-soon panel,
  export menu (CSV/JSON/iCal/Atom), clean shareable URLs, tracker-count social proof.
- **Venue pages:** milestone stepper, all-cycles table, Google/Outlook/.ics calendar links, Web Share, official LaTeX
  preambles per template family, schema.org JSON-LD, OpenGraph tags, breadcrumb, data-quality/verification badges.
- **Comparison:** best-value highlighting, countdowns, per-column remove, shareable full page.
- **Accounts:** password reset/change, email change, JSON data export, account deletion, onboarding checklist,
  weekly digest opt-in, timezone preference.
- **Tracker:** drag & drop between columns, checklist progress bars.
- **Data & admin:** `import_venues` (CSV/JSON, dry-run), `send_digest`, `seed_demo`; cycle verification
  (`verified_at`, `source_url`); admin filters, facets, CSV export and verify actions.
- **API:** dedicated module with pagination links, weak ETags/304, CORS, JSON errors, rate-limit headers; OpenAPI 3.1
  schema; interactive documentation with a live console.
- **Operations:** settings package (local/test/production) with `.env` support, `DATABASE_URL`, Redis cache, WhiteNoise,
  GZip, request-ID logging, nonce CSP, Permissions-Policy, rate limiting, `/healthz`, sitemap, robots.txt, custom
  error pages, deploy system checks.
- **Tooling:** Dockerfile, docker-compose (PostgreSQL/Redis/scheduler), gunicorn config, Procfile, Makefile,
  pre-commit, ruff, coverage, GitHub Actions (lint, tests on SQLite & PostgreSQL, deploy checks, asset freshness,
  Docker smoke test, Playwright e2e + axe).

- **Round 2:** email verification (signed, address-bound, expiring links; reminders/digests only to confirmed
  addresses; rate-limited resend), notifications to trackers when a deadline moves, About/FAQ and Privacy pages,
  recently viewed venues in the command palette, embeddable countdown widget, calendar feeds for venue lists.

### Changed
- Seeding projects one upcoming edition for every dated venue and never overwrites editor-verified cycles.
- Bookmarks belong to a user or an anonymous browser key and merge on login.

### Fixed
- `collectstatic` failed on vendored source-map references; the container could not create its SQLite database as the
  non-root user; aborted HTMX searches logged console errors; drag & drop consumed the flash message.

## [0.2.0]
- Accounts, submission tracker, reminders, community reviews, recommender, planner, insights, lists, saved searches,
  feeds and the token API.

## [0.1.0]
- Initial catalogue, filtering, countdowns, comparison, exports and JSON API.
