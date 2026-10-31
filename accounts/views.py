"""Server-side account endpoints outside the React app: email verification links, data export and calendar feeds."""

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET

from tracker.models import Submission
from venues.ics import build_multi_calendar
from venues.models import DeadlineCycle, VenueBookmark

from .models import UserProfile, VenueList
from .verification import read_token


@require_GET
def verify_email(request, token):
    parsed = read_token(token)
    profile = UserProfile.objects.select_related("user").filter(user_id=parsed[0]).first() if parsed else None
    if profile is None or profile.user.email.lower() != parsed[1]:
        messages.error(request, "This confirmation link is invalid or has expired. Request a new one from your dashboard.")
        return redirect("accounts:dashboard" if request.user.is_authenticated else "accounts:login")
    profile.verified_email = profile.user.email
    profile.save(update_fields=["verified_email"])
    messages.success(request, f"Thanks — {profile.user.email} is confirmed. Reminders are on their way.")
    return redirect("accounts:dashboard" if request.user.is_authenticated else "accounts:login")


@login_required
@require_GET
def export_data(request):
    """GDPR-style export of everything VenuePulse stores about the current user."""
    u = request.user
    p = u.profile

    def iso(v):
        return v.isoformat() if v else None

    data = {
        "exported_at": timezone.now().isoformat(),
        "account": {"username": u.get_username(), "email": u.email, "date_joined": iso(u.date_joined), "last_login": iso(u.last_login)},
        "profile": {
            "display_name": p.display_name,
            "affiliation": p.affiliation,
            "research_interests": p.research_interests,
            "timezone": p.timezone,
            "email_reminders": p.email_reminders,
            "reminder_days": p.reminder_days,
        },
        "bookmarks": [
            {"venue": b.venue.slug, "starred": b.is_starred, "note": b.note, "updated_at": iso(b.updated_at)}
            for b in VenueBookmark.objects.filter(user=u).select_related("venue")
        ],
        "venue_lists": [
            {
                "name": lst.name,
                "slug": lst.slug,
                "public": lst.is_public,
                "description": lst.description,
                "venues": list(lst.venues.values_list("slug", flat=True)),
            }
            for lst in u.venue_lists.prefetch_related("venues")
        ],
        "saved_searches": [{"name": s.name, "query": s.querystring, "alert": s.alert} for s in u.saved_searches.all()],
        "papers": [
            {
                "title": paper.title,
                "abstract": paper.abstract,
                "keywords": paper.keywords,
                "submissions": [
                    {
                        "venue": s.venue.slug,
                        "cycle": s.cycle.year if s.cycle else None,
                        "status": s.status,
                        "submitted_on": iso(s.submitted_on),
                        "decision_on": iso(s.decision_on),
                        "notes": s.notes,
                        "checklist": [{"text": i.text, "done": i.done} for i in s.checklist_items.all()],
                    }
                    for s in paper.submissions.select_related("venue", "cycle").prefetch_related("checklist_items")
                ],
            }
            for paper in u.papers.all()
        ],
        "reviews": [
            {
                "venue": r.venue.slug,
                "rating": r.rating,
                "review_quality": r.review_quality,
                "turnaround_days": r.turnaround_days,
                "outcome": r.outcome,
                "comment": r.comment,
                "created_at": iso(r.created_at),
            }
            for r in u.venue_reviews.select_related("venue")
        ],
        "suggestions": [
            {"cycle": str(s.cycle), "field": s.field, "new_value": iso(s.new_value), "status": s.status, "source_url": s.source_url}
            for s in u.suggestions.select_related("cycle__venue")
        ],
        "notifications": [
            {"message": n.message, "kind": n.kind, "created_at": iso(n.created_at), "read_at": iso(n.read_at)} for n in u.notifications.all()[:1000]
        ],
    }
    response = HttpResponse(json.dumps(data, indent=2, ensure_ascii=False), content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="venuepulse-{u.get_username()}-export.json"'
    return response


@require_GET
def list_calendar(request, slug):
    """iCal feed of every upcoming milestone of a public list's venues (owners can also use private lists)."""
    lst = get_object_or_404(VenueList, slug=slug)
    if not (lst.is_public or (request.user.is_authenticated and lst.user_id == request.user.id)):
        raise Http404
    now = timezone.now()
    cycles = DeadlineCycle.objects.filter(venue__in=lst.venues.all(), submission_deadline__gte=now - timedelta(days=1)).select_related("venue")
    body = build_multi_calendar(f"VenuePulse – {lst.name}", cycles, request.get_host().split(":")[0])
    resp = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = f'inline; filename="{lst.slug}.ics"'
    return resp


@require_GET
def calendar_feed(request, token):
    profile = get_object_or_404(UserProfile.objects.select_related("user"), calendar_token=token)
    now = timezone.now()
    venue_ids = set(VenueBookmark.objects.filter(user=profile.user, is_starred=True).values_list("venue_id", flat=True))
    venue_ids |= set(profile.user.submissions.filter(status__in=Submission.ACTIVE).values_list("venue_id", flat=True))
    cycles = DeadlineCycle.objects.filter(venue_id__in=venue_ids, submission_deadline__gte=now - timedelta(days=1)).select_related("venue")
    if not profile.calendar_subscribed:
        UserProfile.objects.filter(pk=profile.pk).update(calendar_subscribed=True)
    body = build_multi_calendar(f"VenuePulse – {profile.name}", cycles, request.get_host().split(":")[0])
    resp = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = 'inline; filename="venuepulse.ics"'
    return resp
