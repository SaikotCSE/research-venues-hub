#!/usr/bin/env bash
set -o errexit

echo "---> 1. Building frontend..."
node --version  # pinned by .node-version (Vite needs 20.19+ or 22.12+)
npm ci
npm run build

echo "---> 2. Installing Python packages..."
pip install -r requirements.txt

echo "---> 3. Collecting static files..."
python manage.py collectstatic --noinput

echo "---> 4. Migrating database and seeding venues..."
python manage.py migrate --noinput
python manage.py seed_venues

echo "---> 5. Deployment checks (warnings only; e.g. W003 means email is not configured, so sign-up codes can't be sent)..."
python manage.py check --deploy --settings=config.settings.production || true
