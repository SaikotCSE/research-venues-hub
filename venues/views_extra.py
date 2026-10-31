"""Recommender, planner, insights, suggest/autocomplete, token API, feeds."""

from datetime import date

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.feedgenerator import Atom1Feed
from django.views.decorators.http import require_GET

from .filters import filter_venues
from .ics import build_multi_calendar
from .insights import insights_data
from .models import DeadlineCycle, Venue
from .ownership import starred_ids
from .recommend import plan, recommend


def _base():
    return Venue.objects.prefetch_related("subfields", "cycles")


# ----------------------------------------------------------- recommender / planner
@require_GET
def recommend_view(request):
    text = request.GET.get("text", "").strip()[:2000]  # profile interests are only offered as a hint, never used silently
    domain = request.GET.get("domain") or None
    vtype = request.GET.get("type") or None
    results = recommend(text, domain=domain, venue_type=vtype, limit=20) if text else []
    ctx = {
        "text": text,
        "results": results,
        "searched": bool(text),
        "domain": domain,
        "vtype": vtype,
        "domains": list(Venue.objects.order_by("primary_domain").values_list("primary_domain", flat=True).distinct()),
        "type_choices": Venue.VenueType.choices,
        "starred_ids": starred_ids(request),
        "interests": request.user.profile.research_interests if request.user.is_authenticated else "",
    }
    return render(request, "venues/recommend.html", ctx)


@require_GET
def plan_view(request):
    ready = None
    raw = request.GET.get("ready")
    if raw:
        try:
            ready = date.fromisoformat(raw)
        except ValueError:
            ready = None
    rows = plan(ready, domain=request.GET.get("domain") or None, venue_type=request.GET.get("type") or None) if ready else []
    return render(
        request,
        "venues/plan.html",
        {
            "ready": ready,
            "raw": raw or "",
            "rows": rows,
            "today": timezone.localdate(),
            "domains": list(Venue.objects.order_by("primary_domain").values_list("primary_domain", flat=True).distinct()),
            "domain": request.GET.get("domain", ""),
            "type_choices": Venue.VenueType.choices,
            "vtype": request.GET.get("type", ""),
            "tips": [
                ("Pick a realistic date", "Add a week of buffer for internal review, proofreading and the inevitable last-minute experiment."),
                ("Mind the time zone", "Most CS conferences close at 23:59 Anywhere on Earth (UTC−12) — that is already the next day in Europe and Asia."),
                ("Abstracts come first", "Many venues require an abstract registration about a week before the paper deadline."),
            ],
        },
    )


# ----------------------------------------------------------- insights
@require_GET
def insights(request):
    return render(request, "venues/insights.html", {"data": insights_data()})


# ----------------------------------------------------------- calendar & atom feeds
@require_GET
def calendar_filtered(request):
    """Subscribe to every upcoming milestone matching the list filters: /calendar.ics?core=A*&type=Conference"""
    now = timezone.now()
    ids = filter_venues(request.GET).values("pk")
    cycles = DeadlineCycle.objects.filter(venue__in=ids, submission_deadline__gte=now).select_related("venue")[:600]
    resp = HttpResponse(build_multi_calendar("VenuePulse deadlines", cycles, request.get_host().split(":")[0]), content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = 'inline; filename="venuepulse-deadlines.ics"'
    return resp


class DeadlineFeed(Feed):
    feed_type = Atom1Feed
    title = "VenuePulse – upcoming submission deadlines"
    subtitle = "Calls for papers closing soonest"

    def link(self):
        return reverse("venues:list")

    def get_object(self, request):
        return filter_venues(request.GET).values("pk")

    def items(self, ids):
        now = timezone.now()
        return DeadlineCycle.objects.filter(venue__in=ids, submission_deadline__gte=now).select_related("venue").order_by("submission_deadline")[:50]

    def item_title(self, c):
        return f"{c.venue.acronym} {c.year}: paper deadline {c.submission_deadline:%b %d, %Y}"

    def item_description(self, c):
        return f"{c.venue.name}. Paper deadline {c.submission_deadline:%Y-%m-%d %H:%M} UTC ({c.timezone_label}). " + (
            "Dates are projected." if c.is_projected else "Dates confirmed."
        )

    def item_link(self, c):
        return c.venue.get_absolute_url()

    def item_pubdate(self, c):
        return c.submission_open_date or c.submission_deadline

    def item_guid(self, c):
        return f"venuepulse-{c.venue.slug}-{c.year}"

    item_guid_is_permalink = False


# ----------------------------------------------------------- API docs
API_ENDPOINTS = [
    (
        "Catalogue (public)",
        [
            ("GET", "/api/venues/", "Paginated, filterable list of venues"),
            ("GET", "/api/venues/{slug}/", "One venue with every deadline cycle"),
            ("GET", "/api/tags/", "Subfield tags with venue counts"),
            ("GET", "/api/insights/", "Aggregates behind the Insights page"),
            ("GET", "/api/stats/", "Catalogue totals and server time"),
            ("GET", "/api/suggest/?q=", "Autocomplete (up to 8 venues)"),
            ("GET", "/api/openapi.json", "OpenAPI 3.1 description of this API"),
        ],
    ),
    (
        "Your account (bearer token)",
        [
            ("GET", "/api/v1/me/", "Your profile"),
            ("GET", "/api/v1/me/targets/", "Your starred venues"),
            ("POST", "/api/v1/me/targets/", 'Star a venue — body {"slug": "cvpr"}'),
            ("DELETE", "/api/v1/me/targets/{slug}/", "Unstar a venue"),
            ("GET", "/api/v1/me/submissions/", "Your tracked submissions"),
        ],
    ),
    (
        "Feeds & exports (public)",
        [
            ("GET", "/calendar.ics?…", "iCalendar feed of every upcoming milestone matching the filters"),
            ("GET", "/feed/deadlines.atom?…", "Atom feed of the next 50 deadlines"),
            ("GET", "/export/csv/?…", "CSV export (spreadsheet friendly)"),
            ("GET", "/export/json/?…", "JSON export including all cycles (re-importable with import_venues)"),
        ],
    ),
]


@require_GET
def api_docs(request):
    from .openapi import FILTER_PARAMS

    return render(
        request,
        "venues/api_docs.html",
        {
            "host": request.build_absolute_uri("/").rstrip("/"),
            "toc": [
                ("quickstart", "Quick start"),
                ("try", "Try it"),
                ("conventions", "Conventions"),
                ("endpoints", "Endpoints"),
                ("filters", "Filter parameters"),
                ("auth", "Authentication"),
            ],
            "langs": [("curl", "curl"), ("python", "Python"), ("js", "JavaScript")],
            "try_examples": ["/api/venues/?status=open&page_size=3", "/api/venues/neurips/", "/api/tags/", "/api/suggest/?q=icml", "/api/stats/"],
            "limits": settings.RATELIMITS,
            "endpoint_groups": API_ENDPOINTS,
            "filter_params": FILTER_PARAMS,
        },
    )
