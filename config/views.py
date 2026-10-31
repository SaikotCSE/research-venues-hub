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


FAQS = [
    (
        "What does “AoE” mean?",
        "<em>Anywhere on Earth</em> (UTC−12) is the latest time zone on the planet. A deadline of “23:59 AoE” has not passed as long as it is "
        "still that date <em>somewhere</em> — that is already the next day in Europe and Asia. VenuePulse stores every deadline as an exact "
        "instant and shows it in AoE <em>and</em> in your chosen timezone, so you never have to convert by hand.",
    ),
    (
        "Why are some dates marked “Projected”?",
        "Many venues announce their next call only a few months ahead. To help you plan, VenuePulse projects the next edition from the "
        "pattern of previous ones and labels those dates <strong>Projected</strong>. Once an editor checks the official call the cycle "
        "is marked <strong>Verified</strong>, with a link to the source. Always confirm on the official website before you submit.",
    ),
    (
        "How reliable are the ranks and metrics?",
        "They are compiled from public sources (CORE portal, the CCF recommendation list, Google Scholar Metrics, Journal Citation "
        "Reports and Scopus) and are approximate — lists are revised every few years and metrics change annually. Use them as a guide, "
        "not a verdict on a venue’s quality.",
    ),
    (
        "How do reminders work?",
        "Star a venue (or track a submission) and, once your email is confirmed, VenuePulse reminds you before each abstract and paper "
        "deadline — by default 14, 7 and 1 days before. You can change the offsets, switch emails off, or subscribe to a private "
        "calendar feed instead from your profile. If a tracked deadline moves, you get a notification too.",
    ),
    (
        "Can I use VenuePulse without an account?",
        "Yes. Searching, filtering, comparing, exports, feeds and the API are open to everyone, and you can star venues and keep notes "
        "anonymously in your browser. Create a free account to sync them across devices and get reminders — your anonymous stars are kept.",
    ),
    (
        "A date is wrong — how do I fix it?",
        "Open the venue page and choose <em>Suggest a correction</em> (requires an account) with a link to the official call. Editors "
        'review suggestions in the admin; approved changes are logged on the public <a class="link" href="/community/changes/">deadline radar</a>.',
    ),
    (
        "Can I build on the data?",
        'Yes — see the <a class="link" href="/api/docs/">API documentation</a> for the JSON API, OpenAPI schema, CSV/JSON exports and '
        "iCal/Atom feeds. Public endpoints allow cross-origin requests, so you can embed live deadlines in your lab’s website.",
    ),
]

METRICS = [
    ("CORE rank", "Australian CORE conference ranking, widely used in computer science hiring and funding.", "A* (flagship) · A · B · C"),
    ("CCF rank", "China Computer Federation recommended venues list.", "A · B · C"),
    ("h5-index", "Google Scholar: the largest h such that h papers from the last five years have at least h citations each.", "Higher is better"),
    ("h5-median", "Median citations of the papers that make up the h5-index.", "Higher is better"),
    ("Impact factor", "Journal Citation Reports: citations in a year to items published in the previous two years, per item.", "Field-dependent"),
    ("Quartile", "Where a journal’s impact sits within its subject category.", "Q1 (top 25%) – Q4"),
    ("CiteScore / SJR", "Scopus-based citation metrics; SJR weights citations by the prestige of the citing journal.", "Higher is better"),
    ("Acceptance rate", "Share of submitted papers accepted in recent editions.", "Lower = more selective"),
]


@require_GET
def about(request):
    from django.shortcuts import render

    return render(request, "venues/about.html", {"faqs": FAQS, "metrics": METRICS})


@require_GET
def privacy(request):
    from django.shortcuts import render

    return render(request, "venues/privacy.html")
