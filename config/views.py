"""Project-level operational endpoints: health check, robots.txt, web manifest, favicon."""
import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse, HttpResponsePermanentRedirect, JsonResponse
from django.templatetags.static import static
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

logger = logging.getLogger("venuepulse")


@require_GET
@cache_control(no_store=True)
def healthz(request):
    """Liveness/readiness probe: verifies the database and cache are reachable."""
    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:  # pragma: no cover - exercised only when the DB is down
        logger.exception("Health check: database unavailable")
        checks["database"] = "error"
    try:
        cache.set("healthz", "1", 5)
        checks["cache"] = "ok" if cache.get("healthz") == "1" else "error"
    except Exception:  # pragma: no cover
        logger.exception("Health check: cache unavailable")
        checks["cache"] = "error"
    healthy = all(v == "ok" for v in checks.values())
    return JsonResponse({"status": "ok" if healthy else "degraded", **checks}, status=200 if healthy else 503)


@require_GET
@cache_control(max_age=86400, public=True)
def robots_txt(request):
    lines = ["User-agent: *", "Allow: /", "Disallow: /accounts/", "Disallow: /tracker/", "Disallow: /api/v1/", "Disallow: /export/"]
    if settings.ADMIN_URL == "admin/":
        lines.append("Disallow: /admin/")
    lines += ["", f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}", ""]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


@require_GET
@cache_control(max_age=86400, public=True)
def manifest(request):
    data = {
        "name": "VenuePulse — Research Venues & Deadlines",
        "short_name": "VenuePulse",
        "description": "Live countdowns, ranks and submission rules for conferences and journals.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": "#4f46e5",
        "icons": [
            {"src": static("venues/img/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("venues/img/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": static("venues/img/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    response = JsonResponse(data)
    response["Content-Type"] = "application/manifest+json"
    return response


@require_GET
def favicon(request):
    return HttpResponsePermanentRedirect(static("venues/img/favicon-32.png"))
