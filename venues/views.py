"""Server-rendered endpoints that stay outside the React app: calendars, feeds, exports and the embed widget."""

import csv

from django.contrib.syndication.views import Feed
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.utils.feedgenerator import Atom1Feed
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_GET

from config.middleware import build_csp
from config.site import site_base_url

from .filters import filter_venues
from .ics import build_calendar, build_multi_calendar
from .models import DeadlineCycle
from .ownership import bookmarks_for
from .serializers import CSV_COLUMNS, venue_to_csv_row, venue_to_dict
from .services import base_queryset


# ---------------------------------------------------------------- calendars
@require_GET
def venue_ics(request, slug):
    venue = get_object_or_404(base_queryset(), slug=slug)
    now = timezone.now()
    cycles = [c for c in venue.cycles.all() if c.submission_deadline >= now or (c.event_end_date and c.event_end_date >= now.date())]
    if not cycles:
        raise Http404("No upcoming dated milestones for this venue.")
    body = build_calendar(venue, cycles, request.get_host().split(":")[0])
    resp = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{venue.slug}-deadlines.ics"'
    return resp


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


# ---------------------------------------------------------------- embeddable widget
@require_GET
@xframe_options_exempt
def venue_embed(request, slug):
    """Small, frameable countdown card for third-party websites (?theme=dark|light)."""
    venue = get_object_or_404(base_queryset(), slug=slug)
    response = render(
        request,
        "venues/embed.html",
        {
            "venue": venue,
            "cycle": venue.next_cycle,
            "next_deadline": venue.next_deadline,
            "theme": "dark" if request.GET.get("theme") == "dark" else "light",
            "venue_url": site_base_url(request) + venue.get_absolute_url(),
        },
    )
    # Same CSP as everywhere else, except that any site may frame this page.
    response["Content-Security-Policy"] = build_csp(request.csp_nonce).replace("frame-ancestors 'none'", "frame-ancestors *")
    patch_cache_control(response, public=True, max_age=300)
    return response


# ---------------------------------------------------------------- exports
def _export_queryset(request):
    qs = filter_venues(request.GET, base=base_queryset())
    if request.GET.get("scope") == "targets":
        qs = qs.filter(pk__in=bookmarks_for(request).filter(is_starred=True).values("venue_id"))
    return qs


def _csv_safe(value):
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


@require_GET
def export_csv(request):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="venuepulse-venues.csv"'
    writer = csv.writer(resp)
    writer.writerow(CSV_COLUMNS)
    for v in _export_queryset(request):
        writer.writerow([_csv_safe(c) for c in venue_to_csv_row(v)])
    return resp


@require_GET
def export_json(request):
    data = [venue_to_dict(v, detail=True) for v in _export_queryset(request)]
    resp = JsonResponse({"count": len(data), "results": data}, json_dumps_params={"indent": 2})
    resp["Content-Disposition"] = 'attachment; filename="venuepulse-venues.json"'
    return resp
