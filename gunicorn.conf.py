"""Gunicorn configuration (12-factor: everything tunable through the environment)."""
import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 5)))
threads = int(os.environ.get("GUNICORN_THREADS", 2))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 30))
graceful_timeout = 20
keepalive = 5
max_requests = 1000          # recycle workers to bound memory growth
max_requests_jitter = 100
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "*")  # trust the platform's proxy for X-Forwarded-*
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms "%(a)s" req=%({x-request-id}o)s'
