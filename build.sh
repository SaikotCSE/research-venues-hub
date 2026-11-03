#!/usr/bin/env bash
set -o errexit

echo "---> 1. Building frontend..."
npm ci
npm run build

echo "---> 2. Installing Python packages..."
pip install -r requirements.txt

echo "---> 3. Collecting static files..."
python manage.py collectstatic --noinput

echo "---> 4. Migrating database and seeding venues..."
python manage.py migrate --noinput
python manage.py seed_venues
