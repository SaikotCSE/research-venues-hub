# Contributing

Thanks for helping improve VenuePulse!

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install            # ruff + basic hygiene hooks on every commit
python manage.py migrate && python manage.py seed_venues && python manage.py seed_demo
npm ci                        # only needed when touching templates, CSS, icons or e2e tests
```

## Before opening a pull request

- `make lint` — ruff lint and formatting must pass (`make format` fixes most issues).
- `make test` — the Django suite runs with warnings as errors.
- `make check` — includes `check --deploy` against production settings and a missing-migration check.
- If you changed templates or CSS: `npm run build` and commit the regenerated files under `venues/static/venues/`.
  Use `{% icon "name" "classes" %}` for icons (any [Lucide](https://lucide.dev/icons) name); the build adds it to the
  sprite.
- For UI changes, run `npm run e2e` (Playwright + axe accessibility checks) and attach screenshots to the PR.

## Conventions

- Keep views thin: filtering lives in `venues/filters.py`, serialisation in `venues/serializers.py`, API endpoints in
  `venues/api.py`.
- No inline `<script>` or `on*=` handlers — the CSP forbids them. Use Alpine directives (`@click`, `x-data`) and put
  JavaScript in `venues/static/venues/js/`.
- Use the design-system classes in `frontend/styles.css` (`btn-primary`, `card`, `input`, `badge`, `chip`, `muted`, …)
  and always provide dark-mode variants for custom colours.
- Every form control needs a label; icon-only buttons need `aria-label`.
- Add tests with every change. Hot pages have query budgets in `venues/tests_perf.py` — keep them constant.

## Venue data

Data corrections are welcome! Either suggest a correction from the venue page (moderated in the admin) or send a PR
editing `venues/seed_data/`. Please include a link to the official call for papers.
