import csv
import json
from collections import OrderedDict
from datetime import date, timedelta

from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.context_processors import site_base_url

from .filters import active_filters, facet_options, filter_venues, with_tracker_counts
from .ics import build_calendar
from .models import DeadlineCycle, Venue, VenueBookmark
from .ownership import bookmarks_for, get_or_create_bookmark
from .ownership import starred_ids as _starred_ids
from .seo import calendar_links, milestone_steps, structured_data
from .serializers import CSV_COLUMNS, venue_to_csv_row, venue_to_dict
from .timeline import timeline_rows

TABLE_COLUMNS = [
    # (sort key, label, default direction, alignment)
    ("name", "Venue", "asc", ""),
    ("", "Type", "", ""),
    ("rank", "Rank", "desc", ""),
    ("impact_factor", "IF", "desc", "right"),
    ("h5_index", "h5", "desc", "right"),
    ("acceptance_rate", "Accept.", "asc", "right"),
    ("deadline", "Next deadline", "asc", ""),
    ("", "Status", "", ""),
    ("", "Save · Compare", "", "right"),
]
MAX_COMPARE = 4
VIEW_MODES = ("grid", "table", "timeline", "calendar")
PAGE_SIZE = {"grid": 24, "table": 50, "timeline": 40}


# ---------------------------------------------------------------- helpers
def _base_qs():
    return Venue.objects.prefetch_related("subfields", "cycles")


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true" and not request.headers.get("HX-Boosted")


def _calendar_months(venues, now):
    """Group upcoming milestones of the given venues into the next 12 months."""
    months = OrderedDict()
    y, m = now.year, now.month
    for _ in range(12):
        months[(y, m)] = []
        m += 1
        if m == 13:
            y, m = y + 1, 1
    for v in venues:
        for c in v.cycles.all():
            for key, label, dt in c.milestones():
                if key not in ("abstract", "submission", "notification", "camera_ready"):
                    continue
                if dt < now.replace(hour=0, minute=0, second=0, microsecond=0):
                    continue
                k = (dt.year, dt.month)
                if k in months:
                    months[k].append({"venue": v, "label": label, "kind": key, "at": dt})
    out = []
    for (yy, mm), events in months.items():
        events.sort(key=lambda e: e["at"])
        out.append({"year": yy, "month": date(yy, mm, 1), "events": events})
    return out


# ---------------------------------------------------------------- pages
@require_GET
def venue_list(request):
    now = timezone.now()
    view_mode = request.GET.get("view") if request.GET.get("view") in VIEW_MODES else "grid"
    qs = with_tracker_counts(filter_venues(request.GET, base=_base_qs(), now=now))
    total = qs.count()
    ctx = {
        "view_mode": view_mode,
        "total": total,
        "starred_ids": _starred_ids(request),
        "sort": request.GET.get("sort") or "deadline",
        "dir": request.GET.get("dir") or "",
        "params": request.GET,
        "chips": active_filters(request.GET),
        "table_columns": TABLE_COLUMNS,
    }
    qd = request.GET.copy()
    qd.pop("page", None)
    ctx["querystring"] = qd.urlencode()
    if view_mode == "calendar":
        ctx["months"] = _calendar_months(list(qs), now)
    elif view_mode == "timeline":
        timeline = timeline_rows(qs.exclude(is_rolling_submission=True), timezone.localdate())
        page = Paginator(timeline["rows"], PAGE_SIZE["timeline"]).get_page(request.GET.get("page"))
        ctx.update(timeline=timeline, page_obj=page, rolling_hidden=qs.filter(is_rolling_submission=True).count())
    else:
        ctx["page_obj"] = Paginator(qs, PAGE_SIZE[view_mode]).get_page(request.GET.get("page"))
    if _is_htmx(request):
        return render(request, "venues/partials/results.html", ctx)
    ctx.update(facet_options())
    ctx["stats"] = _home_stats(now)
    ctx["closing_soon"] = (
        DeadlineCycle.objects.filter(submission_deadline__gte=now).select_related("venue").order_by("submission_deadline")[:6]
    )
    return render(request, "venues/venue_list.html", ctx)


def _home_stats(now):
    return {
        "venues": Venue.objects.count(),
        "open": Venue.objects.filter(cycles__submission_deadline__gte=now, cycles__submission_open_date__lte=now).distinct().count(),
        "closing_30": DeadlineCycle.objects.filter(submission_deadline__gte=now, submission_deadline__lte=now + timedelta(days=30)).count(),
        "countries": Venue.objects.exclude(country__in=["", "Online"]).values("country").distinct().count(),
    }


@require_GET
def venue_detail(request, slug):
    venue = get_object_or_404(_base_qs(), slug=slug)
    return render(request, "venues/venue_detail.html", _detail_ctx(request, venue))


@require_GET
def venue_modal(request, slug):
    venue = get_object_or_404(_base_qs(), slug=slug)
    return render(request, "venues/partials/venue_modal.html", _detail_ctx(request, venue))


def related_venues(venue, limit=6):
    """Venues sharing the most subfield tags (ties broken by rank)."""
    from django.db.models import Count

    tag_ids = list(venue.subfields.values_list("pk", flat=True))
    if not tag_ids:
        return []
    qs = (Venue.objects.filter(subfields__in=tag_ids).exclude(pk=venue.pk)
          .annotate(shared=Count("subfields", distinct=True)).prefetch_related("cycles")
          .order_by("-shared", "acronym")[:limit])
    return list(qs)


def _detail_ctx(request, venue):
    from community.forms import ReviewForm
    from community.models import DeadlineChange, VenueReview
    from community.views import review_summary

    bm = bookmarks_for(request).filter(venue=venue).first()
    cycles = sorted(venue.cycles.all(), key=lambda c: c.year, reverse=True)
    next_cycle = venue.next_cycle
    page_url = site_base_url(request) + venue.get_absolute_url()
    ctx = {
        "venue": venue,
        "cycles": cycles,
        "next_cycle": next_cycle,
        "next_deadline": venue.next_deadline,
        "steps": milestone_steps(next_cycle),
        "calendar_links": calendar_links(venue, next_cycle, page_url) if next_cycle and venue.next_deadline else {},
        "structured_data": structured_data(venue, next_cycle, page_url),
        "page_url": page_url,
        "bookmark": bm,
        "starred": bool(bm and bm.is_starred),
        "note": bm.note if bm else "",
        "tracking_count": VenueBookmark.objects.filter(venue=venue, is_starred=True).count(),
        "review_stats": review_summary(venue),
        "reviews": venue.reviews.select_related("user__profile")[:10],
        "changes": DeadlineChange.objects.filter(cycle__venue=venue).select_related("cycle")[:10],
        "related": related_venues(venue),
    }
    if request.user.is_authenticated:
        mine = VenueReview.objects.filter(user=request.user, venue=venue).first()
        ctx["review_form"] = ReviewForm(instance=mine)
        ctx["my_review"] = mine
        member_of = set(venue.lists.filter(user=request.user).values_list("pk", flat=True))
        ctx["my_lists"] = [(lst, lst.pk in member_of) for lst in request.user.venue_lists.all()]
    return ctx


@require_GET
def venue_ics(request, slug):
    venue = get_object_or_404(_base_qs(), slug=slug)
    now = timezone.now()
    cycles = [c for c in venue.cycles.all() if c.submission_deadline >= now or (c.event_end_date and c.event_end_date >= now.date())]
    if not cycles:
        raise Http404("No upcoming dated milestones for this venue.")
    body = build_calendar(venue, cycles, request.get_host().split(":")[0])
    resp = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{venue.slug}-deadlines.ics"'
    return resp


@require_GET
def compare(request):
    slugs = list(dict.fromkeys(request.GET.getlist("s")))[:MAX_COMPARE]
    venues = list(_base_qs().filter(slug__in=slugs))
    venues.sort(key=lambda v: slugs.index(v.slug))
    template = "venues/partials/compare_table.html" if _is_htmx(request) else "venues/compare.html"
    remove_links = {}
    for v in venues:
        rest = [s for s in slugs if s != v.slug]
        remove_links[v.slug] = "?" + "&".join(f"s={s}" for s in rest)
    return render(request, template, {
        "venues": venues, "rows": compare_rows(venues), "max_compare": MAX_COMPARE,
        "remove_links": remove_links, "is_drawer": _is_htmx(request),
    })


RANK_SCORE = {"A*": 5, "A": 4, "B": 3, "C": 2, "Q1": 5, "Q2": 4, "Q3": 3, "Q4": 2}


def _best(values, pick):
    """Indices of the best non-null values (max or min); none when fewer than two venues have data."""
    present = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(present) < 2:
        return set()
    target = (max if pick == "max" else min)(v for _, v in present)
    if all(v == target for _, v in present):
        return set()
    return {i for i, v in present if v == target}


def compare_rows(venues):
    """Rows for the comparison table; numeric rows flag the best value(s)."""
    def rank_score(v):
        return max(RANK_SCORE.get(v.core_rank, 0), {"A": 5, "B": 3, "C": 2}.get(v.ccf_rank, 0), RANK_SCORE.get(v.quartile, 0)) or None

    deadlines = [v.next_deadline[1] if v.next_deadline else None for v in venues]
    spec = [
        ("Type", [v.venue_type for v in venues], None, None),
        ("Domain", [v.primary_domain for v in venues], None, None),
        ("Rank", [v.rank_label for v in venues], [rank_score(v) for v in venues], "max"),
        ("h5-index", [v.h5_index for v in venues], [v.h5_index for v in venues], "max"),
        ("Impact factor", [v.impact_factor for v in venues], [v.impact_factor for v in venues], "max"),
        ("Acceptance rate", [f"{v.acceptance_rate:.1f}%" if v.acceptance_rate else None for v in venues], [v.acceptance_rate for v in venues], "min"),
        ("Next deadline", deadlines, deadlines, "min"),
        ("Notification", [v.next_cycle.notification_date if v.next_cycle else None for v in venues], None, None),
        ("Event", [v.next_cycle if v.next_cycle and v.next_cycle.event_start_date else None for v in venues], None, None),
        ("Page limit", [v.page_limit for v in venues], None, None),
        ("Template", [v.formatting_style for v in venues], None, None),
        ("Peer review", [v.review_process for v in venues], None, None),
        ("Open access", [("Yes" + (f" · APC ${v.apc_cost_usd:,}" if v.apc_cost_usd else "")) if v.is_open_access else "No" for v in venues], None, None),
        ("Location", [f"{v.country_flag_emoji} {v.city + ', ' if v.city else ''}{v.country}" for v in venues], None, None),
        ("Publisher", [v.publisher for v in venues], None, None),
    ]
    rows = []
    for label, values, scores, pick in spec:
        best = _best(scores, pick) if scores else set()
        rows.append({"label": label, "key": label.lower().replace(" ", "_").replace("-", "_"),
                     "cells": [{"value": val, "best": i in best} for i, val in enumerate(values)]})
    return rows


# ---------------------------------------------------------------- bookmarks
@require_GET
def targets(request):
    bms = bookmarks_for(request).filter(is_starred=True).select_related("venue").prefetch_related("venue__cycles", "venue__subfields")
    venues = sorted((b.venue for b in bms), key=lambda v: (v.next_deadline is None, v.next_deadline[1] if v.next_deadline else 0))
    return render(request, "venues/targets.html", {"venues": venues, "starred_ids": {v.id for v in venues}})


@require_POST
def toggle_bookmark(request, slug):
    venue = get_object_or_404(Venue, slug=slug)
    bm = get_or_create_bookmark(request, venue)
    bm.is_starred = not bm.is_starred
    bm.save(update_fields=["is_starred", "updated_at"])
    resp = render(request, "venues/partials/star_button.html", {"venue": venue, "starred": bm.is_starred})
    message = f"Saved {venue.acronym} to My Targets" if bm.is_starred else f"Removed {venue.acronym} from My Targets"
    resp["HX-Trigger"] = json.dumps({"toast": {"message": message, "type": "success"}, "targets-changed": True})
    return resp


@require_POST
def save_note(request, slug):
    venue = get_object_or_404(Venue, slug=slug)
    bm = get_or_create_bookmark(request, venue)
    bm.note = request.POST.get("note", "")[:5000]
    bm.save(update_fields=["note", "updated_at"])
    return HttpResponse('<span class="text-emerald-600 dark:text-emerald-400">Saved ✓</span>')


# ---------------------------------------------------------------- export
def _export_queryset(request):
    qs = filter_venues(request.GET, base=_base_qs())
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
