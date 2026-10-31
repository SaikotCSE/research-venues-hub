#!/bin/sh
# Container entrypoint: optionally migrate/seed, then exec the given command.
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  python manage.py migrate --noinput
fi
if [ "${SEED_VENUES:-0}" = "1" ]; then
  python manage.py seed_venues
fi

exec "$@"
