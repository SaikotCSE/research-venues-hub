"""Recommender, planner, insights, suggest/autocomplete, token API, feeds."""
import json
from collections import Counter
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.feedgenerator import Atom1Feed
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from config.ratelimit import hit, ratelimit, too_many_requests

from .filters import filter_venues
from .ics import build_multi_calendar
from .models import DeadlineCycle, Venue, VenueBookmark
from .ownership import starred_ids
from .recommend import plan, recommend
from .serializers import venue_to_dict


def _base():
    return Venue.objects.prefetch_related("subfields", "cycles")


# ----------------------------------------------------------- recommender / planner
@require_GET
def recommend_view(request):
    text = request.GET.get("text", "").strip()
    if not text and request.user.is_authenticated:
        text = ""  # only prefill via the form hint, never silently use profile data
    domain = request.GET.get("domain") or None
    vtype = request.GET.get("type") or None
    results = recommend(text, domain=domain, venue_type=vtype, limit=20) if text else []
    ctx = {
        "text": text, "results": results, "searched": bool(text), "domain": domain, "vtype": vtype,
        "domains": list(Venue.objects.order_by("primary_domain").values_list("primary_domain", flat=True).distinct()),
        "type_choices": Venue.VenueType.choices, "starred_ids": starred_ids(request),
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
    return render(request, "venues/plan.html", {
        "ready": ready, "raw": raw or "", "rows": rows, "today": timezone.localdate(),
        "domains": list(Venue.objects.order_by("primary_domain").values_list("primary_domain", flat=True).distinct()),
        "domain": request.GET.get("domain", ""), "type_choices": Venue.VenueType.choices, "vtype": request.GET.get("type", ""),
    })


# ----------------------------------------------------------- insights
def insights_data():
    now = timezone.now()
    months = []
    y, m = now.year, now.month
    for _ in range(12):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    counts = Counter()
    for dt in DeadlineCycle.objects.filter(submission_deadline__gte=now).values_list("submission_deadline", flat=True):
        counts[(dt.year, dt.month)] += 1
    conf = Venue.objects.exclude(venue_type="Journal")
    journals = Venue.objects.filter(venue_type="Journal")
    scatter = [{"x": float(v.acceptance_rate), "y": v.h5_index, "label": v.acronym}
               for v in conf if v.acceptance_rate is not None and v.h5_index]
    return {
        "deadlines_by_month": {"labels": [date(y, m, 1).strftime("%b %Y") for y, m in months], "values": [counts[k] for k in months]},
        "by_domain": list(Venue.objects.values_list("primary_domain").annotate(n=Count("id")).order_by("-n")),
        "by_type": list(Venue.objects.values_list("venue_type").annotate(n=Count("id")).order_by("-n")),
        "core_distribution": [[r, conf.filter(core_rank=r).count()] for r in ("A*", "A", "B", "C", "Unranked")],
        "quartile_distribution": [[q, journals.filter(quartile=q).count()] for q in ("Q1", "Q2", "Q3", "Q4")],
        "by_continent": list(Venue.objects.exclude(continent="Online").values_list("continent").annotate(n=Count("id")).order_by("-n")),
        "top_impact": [[v.acronym, float(v.impact_factor)] for v in journals.exclude(impact_factor=None).order_by("-impact_factor")[:10]],
        "scatter": scatter,
        "open_access_share": {"open": Venue.objects.filter(is_open_access=True).count(), "closed": Venue.objects.filter(is_open_access=False).count()},
        "totals": {
            "venues": Venue.objects.count(), "cycles": DeadlineCycle.objects.count(),
            "upcoming": DeadlineCycle.objects.filter(submission_deadline__gte=now).count(),
            "closing_30d": DeadlineCycle.objects.filter(submission_deadline__gte=now, submission_deadline__lte=now + timedelta(days=30)).count(),
        },
    }


@require_GET
def insights(request):
    return render(request, "venues/insights.html", {"data": insights_data()})


@ratelimit("api_public", methods=("GET",))
@require_GET
def api_insights(request):
    return JsonResponse(insights_data())


# ----------------------------------------------------------- autocomplete (command palette)
@ratelimit("api_public", methods=("GET",))
@require_GET
def api_suggest(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 1:
        return JsonResponse({"results": []})
    matches = list(Venue.objects.filter(Q(acronym__icontains=q) | Q(name__icontains=q)))
    ql = q.lower()
    # exact acronym > acronym prefix > acronym substring > name match
    matches.sort(key=lambda v: (v.acronym.lower() != ql, not v.acronym.lower().startswith(ql), ql not in v.acronym.lower(), v.acronym.lower()))
    return JsonResponse({"results": [
        {"acronym": v.acronym, "name": v.name, "type": v.venue_type, "url": v.get_absolute_url(), "flag": v.country_flag_emoji}
        for v in matches[:8]]})


# ----------------------------------------------------------- calendar & atom feeds
@require_GET
def calendar_filtered(request):
    """Subscribe to every upcoming milestone matching the list filters: /calendar.ics?core=A*&type=Conference"""
    now = timezone.now()
    ids = filter_venues(request.GET).values("pk")
    cycles = DeadlineCycle.objects.filter(venue__in=ids, submission_deadline__gte=now).select_related("venue")[:600]
    resp = HttpResponse(build_multi_calendar("VenuePulse deadlines", cycles, request.get_host().split(":")[0]),
                        content_type="text/calendar; charset=utf-8")
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
        return (DeadlineCycle.objects.filter(venue__in=ids, submission_deadline__gte=now)
                .select_related("venue").order_by("submission_deadline")[:50])

    def item_title(self, c):
        return f"{c.venue.acronym} {c.year}: paper deadline {c.submission_deadline:%b %d, %Y}"

    def item_description(self, c):
        return f"{c.venue.name}. Paper deadline {c.submission_deadline:%Y-%m-%d %H:%M} UTC ({c.timezone_label}). " + (
            "Dates are projected." if c.is_projected else "Dates confirmed.")

    def item_link(self, c):
        return c.venue.get_absolute_url()

    def item_pubdate(self, c):
        return c.submission_open_date or c.submission_deadline

    def item_guid(self, c):
        return f"venuepulse-{c.venue.slug}-{c.year}"

    item_guid_is_permalink = False


# ----------------------------------------------------------- token-authenticated API
def _token_user(request):
    from accounts.models import UserProfile

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    prof = UserProfile.objects.select_related("user").filter(api_token=header[7:].strip()).first()
    return prof.user if prof else None


def token_required(view):
    @csrf_exempt
    def wrapper(request, *a, **kw):
        user = _token_user(request)
        if not user:
            return JsonResponse({"error": "Missing or invalid bearer token."}, status=401)
        if settings.RATELIMIT_ENABLED:
            allowed, limit, remaining, reset = hit("api_token", f"user:{user.pk}", settings.RATELIMITS["api_token"])
            if not allowed:
                return too_many_requests(request, reset)
        request.api_user = user
        response = view(request, *a, **kw)
        if settings.RATELIMIT_ENABLED:
            response["X-RateLimit-Limit"], response["X-RateLimit-Remaining"] = str(limit), str(remaining)
        return response
    wrapper.__name__ = view.__name__
    return wrapper


@token_required
def api_me(request):
    u = request.api_user
    return JsonResponse({"username": u.get_username(), "name": u.profile.name, "timezone": u.profile.timezone,
                         "interests": u.profile.interest_keywords})


@token_required
def api_me_targets(request):
    u = request.api_user
    if request.method == "POST":
        try:
            slug = json.loads(request.body or b"{}").get("slug", "")
        except (ValueError, AttributeError):
            return JsonResponse({"error": "Invalid JSON body."}, status=400)
        venue = get_object_or_404(Venue, slug=slug)
        bm, _ = VenueBookmark.objects.get_or_create(user=u, venue=venue)
        if not bm.is_starred:
            bm.is_starred = True
            bm.save(update_fields=["is_starred"])
        return JsonResponse(venue_to_dict(venue), status=201)
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed."}, status=405)
    venues = [b.venue for b in VenueBookmark.objects.filter(user=u, is_starred=True).select_related("venue").prefetch_related("venue__cycles", "venue__subfields")]
    return JsonResponse({"count": len(venues), "results": [venue_to_dict(v) for v in venues]})


@token_required
def api_me_target_delete(request, slug):
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed."}, status=405)
    n, _ = VenueBookmark.objects.filter(user=request.api_user, venue__slug=slug).delete()
    return JsonResponse({"removed": bool(n)}, status=200 if n else 404)


@token_required
def api_me_submissions(request):
    subs = request.api_user.submissions.select_related("paper", "venue")
    return JsonResponse({"results": [
        {"id": s.id, "paper": s.paper.title, "venue": s.venue.acronym, "status": s.status,
         "submitted_on": s.submitted_on.isoformat() if s.submitted_on else None,
         "deadline": s.target_deadline.isoformat() if s.target_deadline else None} for s in subs]})


@require_GET
def api_docs(request):
    return render(request, "venues/api_docs.html", {"host": request.build_absolute_uri("/").rstrip("/")})
