# Changelog

All notable changes to this project are documented here. Dates are in UTC.

## [Unreleased]

### Security
- **Sign-up requires email verification.** Creating an account emails a 6-digit code, and the account is created only
  after the code is entered (its address then counts as confirmed). Codes expire after 10 minutes, allow 5 attempts,
  work only in the requesting browser and are stored as HMACs.
- **Password reset uses an emailed code** instead of a link: enter the code and the new password on the same page.
  The response doesn't reveal whether an account exists. Old reset links no longer work.
- **Personal API tokens are stored as SHA-256 hashes and never shown.** The API token and the private calendar-feed
  link are gone from the profile and dashboard, and the app's JSON no longer contains them. Tokens that were already
  copied keep working (the migration hashes them in place). Admins issue tokens with
  `manage.py issue_api_token <username>`; the token endpoints are no longer advertised in the API docs or OpenAPI.
- Dependency upgrades clear every `npm audit` finding: React Router 7.18 (open-redirect fixes), Vite 7.3, Vitest 4.1,
  PostCSS 8.5, ESLint 9.39, typescript-eslint 8.72 (with a patched `minimatch`).

### Changed
- "Profile & API" is now "Profile". Venue pages no longer show the "Embed & API" card; the widget URL
  (`/embed/venue/<slug>/`) and the public API still work.

### Added
- `BREVO_API_KEY`: send email through Brevo's HTTPS API, for hosts that block SMTP (Render's free plan).
- `check --deploy` warns (`venuepulse.W003`) when email isn't configured; `build.sh` prints the deploy checks.
- `.node-version` pins Node 22 for Render builds.
- 23 venues for medical image segmentation, domain generalization and test-time adaptation: MLMI, SPIE Medical
  Imaging, EMBC, BIBM, BMVC and ICIP; MELBA, CMIG, CMPB, IEEE TBME, Medical Physics, AIIM, Radiology: AI, BSPC,
  JMI, IEEE TCSVT, IEEE TMM, CVIU, Pattern Recognition Letters, Neurocomputing, Knowledge-Based Systems, Expert
  Systems with Applications and Scientific Reports.
- "Domain Generalization" and "Test-Time Adaptation" topics on the venues that regularly publish that work
  (MICCAI, MIDL, IEEE TMI, MedIA, CVPR, ICCV, ECCV, NeurIPS, ICML, ICLR), so topic filters and the recommender find them.

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
