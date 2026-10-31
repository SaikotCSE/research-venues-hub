"""Signed-in user endpoints: dashboard, profile & tokens, account settings, notifications, saved searches, venue lists."""

import logging
from datetime import timedelta
from zoneinfo import available_timezones

from django.contrib.auth import logout
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, QueryDict
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from accounts.forms import DeleteAccountForm, EmailChangeForm, ProfileForm, SavedSearchForm, VenueListForm
from accounts.models import SavedSearch, VenueList
from accounts.verification import send_verification_email
from tracker.models import Submission
from venues.filters import filter_venues
from venues.models import DeadlineCycle, Venue
from venues.ownership import bookmarks_for, starred_ids
from venues.recommend import recommend
from venues.services import base_queryset

from ..serializers import cycle_payload, iso, list_payload, notification_payload, submission_payload, venue_card, venue_ref
from .base import ApiError, endpoint, form_error, text
from .session import session_payload

logger = logging.getLogger("venuepulse")


def _calendar_url(request, profile):
    return request.build_absolute_uri(reverse("accounts:calendar_feed", args=[profile.calendar_token]))


# ------------------------------------------------------------------ dashboard
@endpoint("GET", login=True)
def dashboard(request):
    user = request.user
    profile = user.profile
    now = timezone.now()
    starred = bookmarks_for(request).filter(is_starred=True)
    cycles = (
        DeadlineCycle.objects.filter(venue__in=starred.values("venue_id"), submission_deadline__gte=now, submission_deadline__lte=now + timedelta(days=120))
        .select_related("venue")
        .order_by("submission_deadline")
    )
    subs = (
        user.submissions.select_related("paper", "venue", "cycle")
        .filter(status__in=Submission.ACTIVE)
        .annotate(items_total=Count("checklist_items", distinct=True), items_done=Count("checklist_items", filter=Q(checklist_items__done=True), distinct=True))
    )
    target_count = starred.count()
    has_submissions = user.submissions.exists()
    onboarding = [
        {"label": "Add research interests", "done": bool(profile.interest_keywords), "url": reverse("accounts:profile")},
        {"label": "Star a target venue", "done": target_count > 0, "url": reverse("venues:list")},
        {"label": "Track a submission", "done": has_submissions, "url": reverse("tracker:create")},
        {"label": "Subscribe to your calendar feed", "done": profile.calendar_subscribed, "url": reverse("accounts:profile") + "#calendar"},
    ]
    recs = recommend(profile.research_interests, limit=4) if profile.interest_keywords else []
    stars = starred_ids(request)
    return {
        "name": profile.name,
        "target_count": target_count,
        "unread_count": user.notifications.filter(read_at__isnull=True).count(),
        "upcoming": [{"venue": {**venue_ref(c.venue), "rank_label": c.venue.rank_label}, "cycle": cycle_payload(c)} for c in cycles],
        "submissions": [submission_payload(s) for s in subs],
        "status_counts": dict(user.submissions.values_list("status").annotate(n=Count("id"))),
        "notifications": [notification_payload(n) for n in user.notifications.filter(read_at__isnull=True)[:5]],
        "lists": [list_payload(lst) for lst in user.venue_lists.annotate(n=Count("venues"))],
        "saved_searches": [_search_payload(s) for s in user.saved_searches.all()],
        "recommendations": [{"venue": venue_card(r["venue"], stars), "percent": r["percent"], "reasons": r["reasons"]} for r in recs],
        "onboarding": onboarding,
        "calendar_url": _calendar_url(request, profile),
    }


# ------------------------------------------------------------------ profile & tokens
def profile_payload(request):
    p = request.user.profile
    return {
        "display_name": p.display_name,
        "affiliation": p.affiliation,
        "research_interests": p.research_interests,
        "timezone": p.timezone,
        "email_reminders": p.email_reminders,
        "reminder_days": p.reminder_days,
        "weekly_digest": p.weekly_digest,
        "email": request.user.email,
        "email_verified": p.email_verified,
        "username": request.user.get_username(),
        "date_joined": iso(request.user.date_joined),
        "calendar_url": _calendar_url(request, p),
        "calendar_subscribed": p.calendar_subscribed,
        "api_token": p.api_token,
    }


@endpoint("GET", "PUT", login=True)
def profile(request):
    if request.method == "PUT":
        p = request.user.profile
        current = {f: getattr(p, f) for f in ProfileForm.Meta.fields}
        data = {**current, **{k: v for k, v in request.data.items() if k in ProfileForm.Meta.fields}}
        form = ProfileForm(data=data, instance=p)
        if not form.is_valid():
            form_error(form)
        form.save()
    return profile_payload(request)


@endpoint("POST", login=True)
def regenerate_token(request, which):
    if which not in ("calendar", "api"):
        raise Http404("Unknown token type.")
    request.user.profile.regenerate_tokens(calendar=which == "calendar", api=which == "api")
    return {**profile_payload(request), "message": f"New {which} token generated; the old one no longer works."}


@endpoint("POST", login=True)
def set_timezone(request):
    zone = text(request.data, "timezone", 64)
    if zone not in available_timezones():
        raise ApiError("Unknown timezone.", 400, {"timezone": ["Choose a timezone from the list."]})
    profile_obj = request.user.profile
    profile_obj.timezone = zone
    profile_obj.save(update_fields=["timezone"])
    return {"timezone": zone}


@endpoint("GET")
def timezones(request):
    return {"results": sorted(available_timezones())}


# ------------------------------------------------------------------ account settings
@endpoint("POST", login=True)
def change_email(request):
    form = EmailChangeForm(data={"email": text(request.data, "email", 254)}, user=request.user)
    if not form.is_valid():
        form_error(form)
    new = form.cleaned_data["email"]
    changed = new != request.user.email.lower()
    request.user.email = new
    request.user.save(update_fields=["email"])
    if changed:
        send_verification_email(request.user, request)
        message = f"Email address updated — please confirm it via the link we sent to {new}."
    else:
        message = "Email address unchanged."
    return {**session_payload(request, drain_messages=False), "message": message}


@endpoint("POST", login=True)
def delete_account(request):
    form = DeleteAccountForm(data={"password": request.data.get("password", ""), "confirm": text(request.data, "confirm", 10)}, user=request.user)
    if not form.is_valid():
        form_error(form)
    user = request.user
    with transaction.atomic():
        logout(request)
        logger.info("Account deleted: %s", user.pk)
        user.delete()
    return {**session_payload(request, drain_messages=False), "message": "Your account and all associated data were deleted."}


# ------------------------------------------------------------------ notifications
@endpoint("GET", login=True)
def notifications(request):
    items = request.user.notifications.all()[:100]
    return {"results": [notification_payload(n) for n in items], "unread_count": request.user.notifications.filter(read_at__isnull=True).count()}


@endpoint("POST", login=True)
def notifications_read(request):
    qs = request.user.notifications.filter(read_at__isnull=True)
    ids = request.data.get("ids")
    if isinstance(ids, list):
        qs = qs.filter(pk__in=[i for i in ids if isinstance(i, int)])
    marked = qs.update(read_at=timezone.now())
    return {"marked": marked, "unread_count": request.user.notifications.filter(read_at__isnull=True).count()}


# ------------------------------------------------------------------ saved searches
def _search_payload(s):
    return {"id": s.id, "name": s.name, "querystring": s.querystring, "alert": s.alert, "last_count": s.last_count, "created_at": iso(s.created_at)}


@endpoint("GET", "POST", login=True)
def saved_searches(request):
    if request.method == "POST":
        querystring = text(request.data, "querystring", 500).lstrip("?")
        form = SavedSearchForm(data={"name": text(request.data, "name", 80), "querystring": querystring, "alert": bool(request.data.get("alert"))})
        if not form.is_valid():
            form_error(form)
        s = form.save(commit=False)
        s.user = request.user
        s.last_count = filter_venues(QueryDict(s.querystring)).count()
        s.save()
        return {"search": _search_payload(s), "message": f"Saved search “{s.name}”."}
    return {"results": [_search_payload(s) for s in request.user.saved_searches.all()]}


@endpoint("DELETE", login=True)
def saved_search_delete(request, pk):
    get_object_or_404(SavedSearch, pk=pk, user=request.user).delete()
    return {"ok": True}


# ------------------------------------------------------------------ venue lists
@endpoint("GET", "POST", login=True)
def lists(request):
    if request.method == "POST":
        form = VenueListForm(
            data={
                "name": text(request.data, "name", 80),
                "description": text(request.data, "description", 300),
                "is_public": bool(request.data.get("is_public")),
            }
        )
        if not form.is_valid():
            form_error(form)
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        venue_slug = text(request.data, "venue", 80)
        if venue_slug:
            venue = Venue.objects.filter(slug=venue_slug).first()
            if venue:
                obj.venues.add(venue)
        return {"list": list_payload(obj, count=obj.venues.count()), "message": f"Created list “{obj.name}”."}
    return {"results": [list_payload(lst) for lst in request.user.venue_lists.annotate(n=Count("venues"))]}


def _visible_list(request, slug):
    lst = get_object_or_404(VenueList.objects.select_related("user__profile"), slug=slug)
    owner = request.user.is_authenticated and lst.user_id == request.user.id
    if not (lst.is_public or owner):
        raise Http404("No such list.")
    return lst, owner


def list_detail_payload(request, lst, owner):
    venues = sorted(
        base_queryset().filter(lists=lst),
        key=lambda v: (v.next_deadline is None, v.next_deadline[1] if v.next_deadline else 0),
    )
    stars = starred_ids(request)
    return {
        "list": list_payload(lst, count=len(venues)),
        "owner": owner,
        "curator": lst.user.profile.name,
        "share_url": request.build_absolute_uri(reverse("accounts:list_detail", args=[lst.slug])),
        "calendar_url": request.build_absolute_uri(reverse("accounts:list_calendar", args=[lst.slug])),
        "venues": [venue_card(v, stars) for v in venues],
    }


@endpoint("GET", "PATCH", "DELETE")
def list_detail(request, slug):
    lst, owner = _visible_list(request, slug)
    if request.method == "GET":
        return list_detail_payload(request, lst, owner)
    if not owner:
        raise ApiError("Only the owner can change this list.", 403) if request.user.is_authenticated else ApiError("Please log in to continue.", 401)
    if request.method == "DELETE":
        name = lst.name
        lst.delete()
        return {"ok": True, "message": f"Deleted list “{name}”."}
    data = {
        "name": text(request.data, "name", 80) if "name" in request.data else lst.name,
        "description": text(request.data, "description", 300) if "description" in request.data else lst.description,
        "is_public": bool(request.data["is_public"]) if "is_public" in request.data else lst.is_public,
    }
    form = VenueListForm(data=data, instance=lst)
    if not form.is_valid():
        form_error(form)
    form.save()
    return list_detail_payload(request, lst, owner)


@endpoint("POST", login=True)
def list_toggle(request, slug, venue_slug):
    """Add or remove a venue. ``{"member": true|false}`` sets membership explicitly; an empty body toggles it."""
    lst = get_object_or_404(VenueList, slug=slug, user=request.user)
    venue = get_object_or_404(Venue, slug=venue_slug)
    present = lst.venues.filter(pk=venue.pk).exists()
    wanted = request.data.get("member")
    member = (not present) if wanted is None else bool(wanted)
    if member and not present:
        lst.venues.add(venue)
    elif not member and present:
        lst.venues.remove(venue)
    return {
        "member": member,
        "count": lst.venues.count(),
        "message": f"Added {venue.acronym} to “{lst.name}”." if member else f"Removed {venue.acronym} from “{lst.name}”.",
    }
