# Contributing

Thanks for helping improve VenuePulse!

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install            # ruff + basic hygiene hooks on every commit
python manage.py migrate && python manage.py seed_venues && python manage.py seed_demo
npm ci                        # Node 20+: the React app, its tests and the e2e suite
```

Run `make web` (or `npm run dev` plus `VITE_DEV_SERVER_URL=http://localhost:5173 python manage.py runserver`) for a
hot-reloading frontend on <http://localhost:8000>.

## Before opening a pull request

- `make lint` and `make test` — ruff and the Django suite (warnings are errors).
- `make check` — includes `check --deploy` against production settings and a missing-migration check.
- `make test-web` — TypeScript, ESLint and Vitest; `npm run format` applies Prettier (with Tailwind class sorting).
- If you changed anything under `frontend/`: `npm run build` and **commit** the regenerated `webapp/static/webapp/`.
  CI fails when the committed bundle is stale.
- For UI changes, run `npm run e2e` (Playwright + axe accessibility checks) and attach light/dark and mobile
  screenshots to the PR.

## Conventions

**Backend**
- Validation lives in Django forms; app endpoints in `webapp/api/` translate JSON into form data and raise
  `form_error(form)` so the client gets per-field messages. Use the `@endpoint(...)` decorator for method checks,
  `login=True`, JSON parsing and error mapping.
- Filtering lives in `venues/filters.py`, shared catalogue helpers in `venues/services.py`, JSON shapes in
  `webapp/serializers.py` (mirror any change in `frontend/src/lib/types.ts`).
- A new page needs a Django URL that renders the shell (`webapp/views.py`: add it to `PAGES` and `PAGE_MODULES`) and
  a route in `frontend/src/app.tsx`. Keep historic URL names stable.
- Hot endpoints have query budgets in `venues/tests_perf.py` — keep them constant.

**Frontend**
- Build UI from `components/ui/` primitives (Radix-based, shadcn-style) and design tokens (`bg-card`, `text-muted-foreground`,
  `text-brand-text`, …) rather than raw colours, so light and dark themes stay consistent and accessible.
- Server state goes through TanStack Query with keys from `lib/query.ts`; prefer optimistic updates for small writes.
- Every control needs a label (`Field` wires labels, descriptions and errors); icon-only buttons need `aria-label`.
- No inline scripts or `eval` — the CSP forbids them.
- Add tests with every change: Django tests for endpoints, Vitest for logic, Playwright for user flows.

## Venue data

Data corrections are welcome! Either suggest a correction from the venue page (moderated in the admin) or send a PR
editing `venues/seed_data/`. Please include a link to the official call for papers.
