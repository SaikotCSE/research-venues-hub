# Changelog

All notable changes to this project are documented here. Dates are in UTC.

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
