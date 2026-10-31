# Deployment

VenuePulse is a standard 12-factor Django app: configuration comes from the environment, static files are served by
WhiteNoise, and the process is stateless apart from the database (and optional Redis).

## Checklist

1. Set at least `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `SITE_URL` (https://…), `DATABASE_URL` and, behind a custom
   domain, `DJANGO_CSRF_TRUSTED_ORIGINS`. Configure SMTP (`EMAIL_HOST`, …) for reminders and password resets.
2. Run `python manage.py check --deploy --settings=config.settings.production` — it should report no issues.
3. Apply migrations (`migrate`), load data (`seed_venues` and/or `import_venues`), create an admin (`createsuperuser`).
4. Schedule the jobs below.
5. Point your load balancer's health check at `GET /healthz` (returns `503` when the database or cache is down).

## Docker

```bash
docker build -t venuepulse .
docker run -p 8000:8000 \
  -e DJANGO_SECRET_KEY=… -e DJANGO_ALLOWED_HOSTS=venuepulse.example.com -e SITE_URL=https://venuepulse.example.com \
  -e DATABASE_URL=postgres://… -v venuepulse-data:/app/data venuepulse
```

The image runs gunicorn as a non-root user, collects static files at build time, migrates on start
(`RUN_MIGRATIONS=1`, default) and can seed the catalogue (`SEED_VENUES=1`). Without `DATABASE_URL` it uses SQLite in
`/app/data` — mount a volume there. `docker compose up --build` starts web + PostgreSQL + Redis + an hourly scheduler.

## Platform-as-a-service (Render, Railway, Heroku, Fly…)

The `Procfile` defines `release: python manage.py migrate --noinput` and the gunicorn `web` process. Gunicorn reads
`PORT`, `WEB_CONCURRENCY`, `GUNICORN_THREADS` and `GUNICORN_TIMEOUT` (see `gunicorn.conf.py`).

## Scheduled jobs

| Command | Suggested schedule | Purpose |
|---|---|---|
| `python manage.py send_reminders` | hourly | Deadline reminders at each user's offsets + saved-search alerts (idempotent) |
| `python manage.py send_digest --if-due` | hourly or daily | Weekly digest; `--if-due` skips users who got one in the last 7 days |

## Reverse proxy & TLS

- Terminate TLS at the proxy and forward `X-Forwarded-Proto: https` (trusted via `SECURE_PROXY_SSL_HEADER`).
- Set `RATELIMIT_USE_X_FORWARDED_FOR=1` **only** if the proxy overwrites `X-Forwarded-For`; otherwise clients could spoof
  their address to evade rate limits.
- With more than one worker or instance, set `REDIS_URL` so rate limits and caches are shared.

## Security headers

`config.middleware.SecurityHeadersMiddleware` sends a nonce-based Content-Security-Policy and a Permissions-Policy.
To trial CSP changes safely set `CSP_REPORT_ONLY=1`. HSTS is enabled with `includeSubDomains` and `preload` by default
(`DJANGO_SECURE_HSTS_*` to adjust) — only submit your domain to the preload list when you are sure.

## Backups & data

- Back up the database regularly; everything else is reproducible from the repository.
- Users can export their own data (`/accounts/settings/`) and delete their account at any time.
- Editors verify projected dates in the admin (*Mark dates as verified*); re-running `seed_venues` never overwrites
  verified cycles.
