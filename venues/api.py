"""JSON API: public read-only catalogue endpoints and bearer-token "me" endpoints.

Conventions
* Errors are JSON: ``{"error": "..."}`` with the matching HTTP status (400/401/404/405/429).
* Lists are paginated: ``count``, ``page``, ``num_pages``, ``page_size``, ``next``, ``previous``, ``results``.
* Public GET endpoints send ``ETag``/``Cache-Control`` (304 on ``If-None-Match``) and CORS ``*``.
* Rate limits are reported in ``X-RateLimit-*`` headers (see settings.RATELIMITS).
"""

import functools
import hashlib
import json
import time

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponseNotModified, JsonResponse
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.views.decorators.csrf import csrf_exempt

from config.ratelimit import hit, ratelimit, too_many_requests

from .filters import filter_venues
from .insights import insights_data
from .models import ResearchSubfield, Venue, VenueBookmark, catalog_version
from .serializers import venue_to_dict


# ------------------------------------------------------------------ helpers
def error(message, status):
    return JsonResponse({"error": message}, status=status)


def api_view(methods=("GET",), public=True):
    """JSON-only view wrapper: method check, JSON 404s, CORS + caching headers for public GETs."""

    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method == "OPTIONS" and public:
                response = JsonResponse({}, status=204)
            elif request.method not in methods:
                response = error(f"Method {request.method} not allowed.", 405)
                response["Allow"] = ", ".join(methods)
            else:
                try:
                    response = view(request, *args, **kwargs)
                except Http404 as exc:
                    response = error(str(exc) or "Not found.", 404)
            if public:
                response["Access-Control-Allow-Origin"] = "*"
                response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
                response["Access-Control-Allow-Headers"] = "If-None-Match"
                response["Access-Control-Expose-Headers"] = "ETag, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset"
            return response

        return wrapper

    return decorator


def conditional(request, response, *parts):
    """Attach a weak ETag derived from the catalogue version, the hour and ``parts``; 304 when it matches."""
    bucket = int(time.time() // 3600)  # deadline-derived fields roll over with time
    raw = "|".join(str(p) for p in (catalog_version(), bucket, request.get_full_path(), *parts))
    etag = f'W/"{hashlib.sha256(raw.encode()).hexdigest()[:20]}"'
    if etag in [t.strip() for t in request.headers.get("If-None-Match", "").split(",")]:
        not_modified = HttpResponseNotModified()
        not_modified["ETag"] = etag
        return not_modified
    response["ETag"] = etag
    patch_cache_control(response, public=True, max_age=300)
    return response


def absolute(request, path):
    return request.build_absolute_uri(path)


def _base():
    return Venue.objects.prefetch_related("subfields", "cycles")


def _page_size(request, default=25, maximum=200):
    try:
        return max(1, min(int(request.GET.get("page_size", default)), maximum))
    except (TypeError, ValueError):
        return default


def _page_link(request, number):
    params = request.GET.copy()
    params["page"] = number
    return absolute(request, f"{request.path}?{params.urlencode()}")


# ------------------------------------------------------------------ public endpoints
@ratelimit("api_public", methods=("GET",))
@api_view()
def venues(request):
    size = _page_size(request)
    page = Paginator(filter_venues(request.GET, base=_base()), size).get_page(request.GET.get("page"))
    data = {
        "count": page.paginator.count,
        "page": page.number,
        "num_pages": page.paginator.num_pages,
        "page_size": size,
        "next": _page_link(request, page.next_page_number()) if page.has_next() else None,
        "previous": _page_link(request, page.previous_page_number()) if page.has_previous() else None,
        "results": [venue_to_dict(v, request=request) for v in page],
    }
    return conditional(request, JsonResponse(data))


@ratelimit("api_public", methods=("GET",))
@api_view()
def venue_detail(request, slug):
    venue = _base().filter(slug=slug).first()
    if venue is None:
        raise Http404(f"No venue with slug '{slug}'.")
    return conditional(request, JsonResponse(venue_to_dict(venue, detail=True, request=request)))


@ratelimit("api_public", methods=("GET",))
@api_view()
def tags(request):
    qs = ResearchSubfield.objects.annotate(n=Count("venues")).filter(n__gt=0).order_by("name")
    return conditional(request, JsonResponse({"count": qs.count(), "results": [{"name": t.name, "slug": t.slug, "venues": t.n} for t in qs]}))


@ratelimit("api_public", methods=("GET",))
@api_view()
def stats(request):
    now = timezone.now()
    return JsonResponse(
        {
            "venues": Venue.objects.count(),
            "by_type": dict(Venue.objects.values_list("venue_type").annotate(n=Count("id"))),
            "with_upcoming_deadline": Venue.objects.filter(cycles__submission_deadline__gte=now).distinct().count(),
            "server_time": now.isoformat(),
        }
    )


@ratelimit("api_public", methods=("GET",))
@api_view()
def insights(request):
    return conditional(request, JsonResponse(insights_data()))


@ratelimit("api_public", methods=("GET",))
@api_view()
def suggest(request):
    q = request.GET.get("q", "").strip()[:80]
    if not q:
        return JsonResponse({"results": []})
    matches = list(
        Venue.objects.filter(Q(acronym__icontains=q) | Q(name__icontains=q)).only("acronym", "name", "slug", "venue_type", "country_flag_emoji")[:50]
    )
    ql = q.lower()
    # exact acronym > acronym prefix > acronym substring > name match
    matches.sort(key=lambda v: (v.acronym.lower() != ql, not v.acronym.lower().startswith(ql), ql not in v.acronym.lower(), v.acronym.lower()))
    return JsonResponse(
        {
            "results": [
                {"acronym": v.acronym, "name": v.name, "type": v.venue_type, "url": v.get_absolute_url(), "flag": v.country_flag_emoji} for v in matches[:8]
            ]
        }
    )


# ------------------------------------------------------------------ token-authenticated endpoints
def _token_user(request):
    from accounts.models import UserProfile, hash_token

    header = request.headers.get("Authorization", "")
    raw = header[7:].strip() if header.startswith("Bearer ") else ""
    if not raw:
        return None
    profile = UserProfile.objects.select_related("user").filter(api_token=hash_token(raw)).first()
    return profile.user if profile and profile.user.is_active else None


def token_required(view):
    @csrf_exempt
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        user = _token_user(request)
        if not user:
            response = error("Missing or invalid bearer token.", 401)
            response["WWW-Authenticate"] = 'Bearer realm="venuepulse"'
            return response
        limit = remaining = None
        if settings.RATELIMIT_ENABLED:
            allowed, limit, remaining, reset = hit("api_token", f"user:{user.pk}", settings.RATELIMITS["api_token"])
            if not allowed:
                return too_many_requests(request, reset)
        request.api_user = user
        response = view(request, *args, **kwargs)
        if limit is not None:
            response["X-RateLimit-Limit"], response["X-RateLimit-Remaining"] = str(limit), str(remaining)
        return response

    return wrapper


@token_required
@api_view(methods=("GET",), public=False)
def me(request):
    u = request.api_user
    return JsonResponse({"username": u.get_username(), "name": u.profile.name, "timezone": u.profile.timezone, "interests": u.profile.interest_keywords})


@token_required
@api_view(methods=("GET", "POST"), public=False)
def me_targets(request):
    u = request.api_user
    if request.method == "POST":
        try:
            slug = json.loads(request.body or b"{}").get("slug", "")
        except (ValueError, AttributeError):
            return error('Invalid JSON body; expected {"slug": "..."}.', 400)
        venue = _base().filter(slug=slug).first()
        if venue is None:
            raise Http404(f"No venue with slug '{slug}'.")
        bm, _ = VenueBookmark.objects.get_or_create(user=u, venue=venue)
        if not bm.is_starred:
            bm.is_starred = True
            bm.save(update_fields=["is_starred"])
        return JsonResponse(venue_to_dict(venue, request=request), status=201)
    bookmarks = VenueBookmark.objects.filter(user=u, is_starred=True).select_related("venue").prefetch_related("venue__cycles", "venue__subfields")
    results = [venue_to_dict(b.venue, request=request) for b in bookmarks]
    return JsonResponse({"count": len(results), "results": results})


@token_required
@api_view(methods=("DELETE",), public=False)
def me_target_delete(request, slug):
    deleted, _ = VenueBookmark.objects.filter(user=request.api_user, venue__slug=slug).delete()
    if not deleted:
        raise Http404(f"'{slug}' is not in your targets.")
    return JsonResponse({"removed": True})


@token_required
@api_view(methods=("GET",), public=False)
def me_submissions(request):
    subs = request.api_user.submissions.select_related("paper", "venue", "cycle")
    return JsonResponse(
        {
            "count": subs.count(),
            "results": [
                {
                    "id": s.id,
                    "paper": s.paper.title,
                    "venue": s.venue.acronym,
                    "venue_slug": s.venue.slug,
                    "status": s.status,
                    "submitted_on": s.submitted_on.isoformat() if s.submitted_on else None,
                    "decision_on": s.decision_on.isoformat() if s.decision_on else None,
                    "deadline": s.target_deadline.isoformat() if s.target_deadline else None,
                }
                for s in subs
            ],
        }
    )
