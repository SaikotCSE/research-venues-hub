"""Catalogue endpoints: facets, explore views, venue detail, stars & notes, targets, compare, recommender, planner, radar."""

from datetime import date

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from community.models import DeadlineChange, VenueReview
from community.services import review_summary
from config.site import site_base_url
from venues.filters import active_filters, facet_options, filter_venues, with_tracker_counts
from venues.models import DeadlineCycle, Venue, VenueBookmark
from venues.openapi import API_ENDPOINTS, FILTER_PARAMS
from venues.ownership import bookmarks_for, get_or_create_bookmark, starred_ids
from venues.recommend import plan, recommend
from venues.seo import calendar_links, milestone_steps
from venues.services import MAX_COMPARE, base_queryset, calendar_months, compare_rows, home_stats, related_venues
from venues.timeline import timeline_rows

from ..serializers import change_payload, cycle_payload, iso, venue_card, venue_ref
from .base import endpoint

PAGE_SIZES = {"grid": 24, "table": 50, "timeline": 40}


# ------------------------------------------------------------------ facets & home
def facets_payload():
    f = facet_options()
    return {
        "domains": f["domains"],
        "countries": f["countries"],
        "continents": f["continents"],
        "tags": f["tags"],
        "types": [value for value, _ in f["type_choices"]],
        "core": [value for value, _ in f["core_choices"]],
        "ccf": [value for value, _ in f["ccf_choices"]],
        "quartiles": [value for value, _ in f["quartile_choices"]],
        "review": [value for value, _ in f["review_choices"]],
        "status": [{"value": v, "label": label} for v, label in f["status_choices"]],
        "within": [{"value": v, "label": label} for v, label in f["within_choices"]],
        "sort": [{"value": v, "label": label} for v, label in f["sort_options"]],
    }


def home_payload():
    now = timezone.now()
    closing = DeadlineCycle.objects.filter(submission_deadline__gte=now).select_related("venue").order_by("submission_deadline")[:6]
    return {
        "stats": home_stats(now),
        "closing_soon": [{"venue": {**venue_ref(c.venue), "rank_label": c.venue.rank_label}, "cycle": cycle_payload(c)} for c in closing],
    }


@endpoint("GET")
def facets(request):
    return facets_payload()


@endpoint("GET")
def home(request):
    return home_payload()


# ------------------------------------------------------------------ explore
def explore_payload(request, params):
    view = "table" if params.get("view") == "table" else "grid"
    qs = with_tracker_counts(filter_venues(params, base=base_queryset()))
    page = Paginator(qs, PAGE_SIZES[view]).get_page(params.get("page"))
    stars = starred_ids(request)
    return {
        "total": page.paginator.count,
        "page": page.number,
        "num_pages": page.paginator.num_pages,
        "page_size": PAGE_SIZES[view],
        "chips": active_filters(params),
        "results": [venue_card(v, stars) for v in page],
    }


def timeline_payload(request, params):
    qs = filter_venues(params, base=base_queryset())
    data = timeline_rows(qs.exclude(is_rolling_submission=True), timezone.localdate())
    page = Paginator(data["rows"], PAGE_SIZES["timeline"]).get_page(params.get("page"))
    stars = starred_ids(request)
    rows = []
    for r in page:
        v, c = r["venue"], r["cycle"]
        rows.append(
            {
                "venue": {**venue_ref(v), "rank_label": v.rank_label, "starred": v.id in stars},
                "cycle": {"id": c.id, "label": str(c), "is_projected": c.is_projected},
                "summary": r["summary"],
                "segments": [
                    {"kind": s["kind"], "label": s["label"], "left": s["left"], "width": s["width"], "start": iso(s["start"]), "end": iso(s["end"])}
                    for s in r["segments"]
                ],
                "markers": [{"label": m["label"], "left": m["left"], "at": iso(m["at"])} for m in r["markers"]],
            }
        )
    return {
        "total": qs.count(),
        "row_count": len(data["rows"]),
        "rolling_hidden": qs.filter(is_rolling_submission=True).count(),
        "page": page.number,
        "num_pages": page.paginator.num_pages,
        "page_size": PAGE_SIZES["timeline"],
        "chips": active_filters(params),
        "today": data["today"],
        "ticks": data["ticks"],
        "rows": rows,
    }


def calendar_payload(request, params):
    now = timezone.now()
    venues = list(filter_venues(params, base=base_queryset(), now=now))
    months = calendar_months(venues, now)
    return {
        "total": len(venues),
        "chips": active_filters(params),
        "months": [
            {
                "year": m["year"],
                "month": m["month"].month,
                "label": m["month"].strftime("%B %Y"),
                "events": [
                    {
                        "venue": venue_ref(e["venue"]),
                        "cycle": str(e["cycle"]),
                        "is_projected": e["cycle"].is_projected,
                        "label": e["label"],
                        "kind": e["kind"],
                        "at": iso(e["at"]),
                    }
                    for e in m["events"]
                ],
            }
            for m in months
        ],
    }


@endpoint("GET")
def explore(request):
    return explore_payload(request, request.GET)


@endpoint("GET")
def explore_timeline(request):
    return timeline_payload(request, request.GET)


@endpoint("GET")
def explore_calendar(request):
    return calendar_payload(request, request.GET)


# ------------------------------------------------------------------ venue detail
def review_payload(r, request):
    return {
        "id": r.id,
        "rating": r.rating,
        "review_quality": r.review_quality,
        "turnaround_days": r.turnaround_days,
        "outcome": r.outcome,
        "outcome_label": r.get_outcome_display(),
        "comment": r.comment,
        "created_at": iso(r.created_at),
        "author": r.user.profile.name,
        "mine": request.user.is_authenticated and r.user_id == request.user.id,
    }


def venue_payload(request, venue):
    """Everything the venue page needs, including the caller's own state (star, note, lists, review)."""
    now = timezone.now()
    bm = bookmarks_for(request).filter(venue=venue).first()
    starred = bool(bm and bm.is_starred)
    next_cycle = venue.next_cycle
    page_url = site_base_url(request) + venue.get_absolute_url()
    cycles = sorted(venue.cycles.all(), key=lambda c: c.year, reverse=True)
    has_upcoming = any(c.submission_deadline >= now or (c.event_end_date and c.event_end_date >= now.date()) for c in cycles)
    me = {"starred": starred, "note": bm.note if bm else "", "note_updated_at": iso(bm.updated_at) if bm and bm.note else None, "lists": None, "review": None}
    if request.user.is_authenticated:
        member_of = set(venue.lists.filter(user=request.user).values_list("pk", flat=True))
        me["lists"] = [{"slug": lst.slug, "name": lst.name, "member": lst.pk in member_of} for lst in request.user.venue_lists.all()]
        mine = VenueReview.objects.filter(user=request.user, venue=venue).select_related("user__profile").first()
        me["review"] = review_payload(mine, request) if mine else None
    return {
        **venue_card(venue, {venue.id} if starred else frozenset()),
        "description": venue.description,
        "scope": venue.scope,
        "h5_median": venue.h5_median,
        "citescore": float(venue.citescore) if venue.citescore is not None else None,
        "sjr": float(venue.sjr) if venue.sjr is not None else None,
        "issn": venue.issn,
        "page_limit": venue.page_limit,
        "formatting_style": venue.formatting_style,
        "template_url": venue.template_url,
        "apc_cost_usd": venue.apc_cost_usd,
        "publisher": venue.publisher,
        "official_website": venue.official_website,
        "submission_portal_url": venue.submission_portal_url,
        "cycles": [cycle_payload(c) for c in cycles],
        "steps": [{"label": s["label"], "when": iso(s["when"]), "state": s["state"], "is_date": s["is_date"]} for s in milestone_steps(next_cycle)],
        "calendar_links": calendar_links(venue, next_cycle, page_url) if next_cycle and venue.next_deadline else {},
        "checklist": [{"label": label, "value": value} for label, value in venue.checklist],
        "latex": venue.latex_snippet,
        "bibtex": venue.bibtex,
        "tracking_count": VenueBookmark.objects.filter(venue=venue, is_starred=True).count(),
        "review_stats": review_summary(venue),
        "reviews": [review_payload(r, request) for r in venue.reviews.select_related("user__profile")[:10]],
        "changes": [change_payload(ch) for ch in DeadlineChange.objects.filter(cycle__venue=venue).select_related("cycle__venue")[:10]],
        "related": [venue_card(v) for v in related_venues(venue)],
        "urls": {
            "page": page_url,
            "ics": reverse("venues:ics", args=[venue.slug]) if has_upcoming else None,
        },
        "me": me,
    }


@endpoint("GET")
def venue_detail(request, slug):
    return venue_payload(request, get_object_or_404(base_queryset(), slug=slug))


@endpoint("POST")
def venue_star(request, slug):
    """Star/unstar a venue. ``{"starred": true|false}`` sets the state explicitly; an empty body toggles it."""
    venue = get_object_or_404(Venue, slug=slug)
    bm = get_or_create_bookmark(request, venue)
    wanted = request.data.get("starred")
    bm.is_starred = (not bm.is_starred) if wanted is None else bool(wanted)
    bm.save(update_fields=["is_starred", "updated_at"])
    return {
        "starred": bm.is_starred,
        "target_count": bookmarks_for(request).filter(is_starred=True).count(),
        "message": f"Saved {venue.acronym} to My Targets" if bm.is_starred else f"Removed {venue.acronym} from My Targets",
    }


@endpoint("PUT")
def venue_note(request, slug):
    venue = get_object_or_404(Venue, slug=slug)
    note = request.data.get("note", "")
    bm = get_or_create_bookmark(request, venue)
    bm.note = (note if isinstance(note, str) else "")[:5000]
    bm.save(update_fields=["note", "updated_at"])
    return {"note": bm.note, "updated_at": iso(bm.updated_at)}


# ------------------------------------------------------------------ targets & compare
@endpoint("GET")
def targets(request):
    bms = bookmarks_for(request).filter(is_starred=True).select_related("venue").prefetch_related("venue__cycles", "venue__subfields")
    pairs = [(b.venue, b.note) for b in bms]
    pairs.sort(key=lambda p: (p[0].next_deadline is None, p[0].next_deadline[1] if p[0].next_deadline else 0))
    ids = {v.id for v, _ in pairs}
    return {"count": len(pairs), "results": [{**venue_card(v, ids), "note": note} for v, note in pairs]}


@endpoint("GET")
def compare(request):
    slugs = list(dict.fromkeys(s for s in request.GET.getlist("s") if s))[:MAX_COMPARE]
    venues = sorted(base_queryset().filter(slug__in=slugs), key=lambda v: slugs.index(v.slug))
    stars = starred_ids(request)
    return {"max": MAX_COMPARE, "venues": [venue_card(v, stars) for v in venues], "rows": compare_rows(venues)}


# ------------------------------------------------------------------ recommender & planner
def _domains():
    return list(Venue.objects.order_by("primary_domain").values_list("primary_domain", flat=True).distinct())


@endpoint("GET")
def recommend_view(request):
    query = request.GET.get("text", "").strip()[:2000]
    results = recommend(query, domain=request.GET.get("domain") or None, venue_type=request.GET.get("type") or None, limit=20) if query else []
    stars = starred_ids(request)
    return {
        "text": query,
        "domains": _domains(),
        "interests": request.user.profile.research_interests if request.user.is_authenticated else "",
        "results": [{"venue": venue_card(r["venue"], stars), "percent": r["percent"], "reasons": r["reasons"]} for r in results],
    }


@endpoint("GET")
def plan_view(request):
    ready = None
    try:
        ready = date.fromisoformat(request.GET.get("ready", ""))
    except ValueError:
        ready = None
    rows = plan(ready, domain=request.GET.get("domain") or None, venue_type=request.GET.get("type") or None) if ready else []
    stars = starred_ids(request)
    return {
        "ready": iso(ready),
        "today": iso(timezone.localdate()),
        "domains": _domains(),
        "rows": [
            {
                "venue": {
                    **venue_ref(r["venue"]),
                    "rank_label": r["venue"].rank_label,
                    "primary_domain": r["venue"].primary_domain,
                    "subfields": [{"slug": s.slug, "name": s.name} for s in r["venue"].subfields.all()],
                    "starred": r["venue"].id in stars,
                },
                "cycle": cycle_payload(r["cycle"]),
                "slack_days": r["slack_days"],
            }
            for r in rows
        ],
    }


# ------------------------------------------------------------------ community radar, options, API docs
@endpoint("GET")
def radar(request):
    items = DeadlineChange.objects.select_related("cycle__venue").order_by("-changed_at")[:100]
    return {"results": [change_payload(ch) for ch in items]}


@endpoint("GET")
def venue_options(request):
    """Compact venue + cycle list for pickers (tracker form, lists)."""
    venues = Venue.objects.order_by("acronym").prefetch_related(Prefetch("cycles", queryset=DeadlineCycle.objects.order_by("-year")))
    return {
        "results": [
            {
                **venue_ref(v),
                "cycles": [{"id": c.id, "year": c.year, "label": str(c), "submission_deadline": iso(c.submission_deadline)} for c in v.cycles.all()],
            }
            for v in venues
        ]
    }


@endpoint("GET")
def api_meta(request):
    return {
        "host": request.build_absolute_uri("/").rstrip("/"),
        "groups": [{"title": title, "endpoints": [{"method": m, "path": p, "description": d} for m, p, d in rows]} for title, rows in API_ENDPOINTS],
        "filters": [{"name": n, "type": t, "description": d} for n, t, d in FILTER_PARAMS],
        "limits": settings.RATELIMITS,
        "examples": ["/api/venues/?status=open&page_size=3", "/api/venues/neurips/", "/api/tags/", "/api/suggest/?q=icml", "/api/stats/"],
    }
