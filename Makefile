# Common developer tasks. Run `make help` for the list.
PY ?= python
MANAGE = $(PY) manage.py

.PHONY: help install dev migrate seed demo run web test test-web e2e coverage lint format check assets docker-up docker-down

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Install Python dev dependencies
	$(PY) -m pip install -r requirements-dev.txt

dev: install migrate seed  ## One-shot local setup (install, migrate, seed)

migrate:  ## Apply database migrations
	$(MANAGE) migrate

seed:  ## Load the venue catalogue (idempotent)
	$(MANAGE) seed_venues

demo:  ## Create a demo account with sample data
	$(MANAGE) seed_demo

run:  ## Start Django using the committed React bundle
	$(MANAGE) runserver

web:  ## Hot-reloading frontend: Vite dev server + Django (open http://localhost:8000)
	@trap 'kill 0' INT TERM EXIT; npm run dev & VITE_DEV_SERVER_URL=http://localhost:5173 $(MANAGE) runserver

test:  ## Run the Django test-suite (warnings are errors)
	$(PY) -W error manage.py test

test-web:  ## Type-check, lint and unit-test the React app
	npm run typecheck && npm run lint && npm test

e2e:  ## Browser end-to-end + accessibility tests (Playwright)
	npm run e2e

coverage:  ## Run tests with coverage report
	coverage run manage.py test && coverage report

lint:  ## Lint and check formatting
	ruff check . && ruff format --check .

format:  ## Auto-fix lint issues and format code
	ruff check --fix . && ruff format .

check:  ## Django system checks incl. deployment checks against production settings
	$(MANAGE) check
	$(MANAGE) makemigrations --check --dry-run
	DJANGO_SECRET_KEY=$$($(PY) -c "import secrets; print(secrets.token_urlsafe(50))") DJANGO_ALLOWED_HOSTS=example.com SITE_URL=https://example.com \
		$(MANAGE) check --deploy --fail-level WARNING --settings=config.settings.production

assets:  ## Rebuild the React bundle into webapp/static/webapp/ (needs Node 20+); commit the result
	npm ci && npm run build

docker-up:  ## Start the production-like stack (web, postgres, redis, scheduler)
	docker compose up --build

docker-down:  ## Stop the stack
	docker compose down
