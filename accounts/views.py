import json
import logging
from datetime import timedelta
from zoneinfo import available_timezones

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import Http404, HttpResponse, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from config.ratelimit import ratelimit
from tracker.models import Submission
from venues.filters import filter_venues
from venues.ics import build_multi_calendar
from venues.models import DeadlineCycle, Venue, VenueBookmark
from venues.ownership import bookmarks_for, starred_ids
from venues.recommend import recommend

from .forms import (
    DeleteAccountForm,
    EmailChangeForm,
    ProfileForm,
    SavedSearchForm,
    SignUpForm,
    StyledAuthForm,
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
    VenueListForm,
)
from .models import SavedSearch, UserProfile, VenueList
from .verification import read_token, send_verification_email

logger = logging.getLogger("venuepulse")


# ------------------------------------------------------------------ authentication
class SignInView(auth_views.LoginView):
    authentication_form = StyledAuthForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    extra_context = {"title": "Welcome back", "submit": "Log in"}


class PasswordResetView(auth_views.PasswordResetView):
    form_class = StyledPasswordResetForm
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/email/password_reset.txt"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = StyledSetPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordChangeView(auth_views.PasswordChangeView):
    form_class = StyledPasswordChangeForm
    template_name = "accounts/form_page.html"
    success_url = reverse_lazy("accounts:settings")
    extra_context = {"title": "Change password", "submit": "Update password", "back_url": reverse_lazy("accounts:settings")}

    def form_valid(self, form):
        messages.success(self.request, "Your password was changed.")
        return super().form_valid(form)


def _safe_next(request, default):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return nxt
    return default


@ratelimit("signup")
def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        logger.info("New account registered: %s", user.pk)
        send_verification_email(user, request)
        messages.success(request, f"Welcome to VenuePulse! We sent a confirmation link to {user.email}. Meanwhile, add a few research interests.")
        return redirect(_safe_next(request, reverse("accounts:profile")))
    return render(request, "accounts/signup.html", {"form": form, "next": request.GET.get("next", "")})


# ------------------------------------------------------------------ dashboard & profile
@login_required
def dashboard(request):
    now = timezone.now()
    horizon = now + timedelta(days=120)
    cycles = (
        DeadlineCycle.objects.filter(
            venue__in=bookmarks_for(request).filter(is_starred=True).values("venue_id"),
            submission_deadline__gte=now,
            submission_deadline__lte=horizon,
        )
        .select_related("venue")
        .order_by("submission_deadline")
    )
    subs = request.user.submissions.select_related("paper", "venue", "cycle").filter(status__in=Submission.ACTIVE)
    status_counts = dict(request.user.submissions.values_list("status").annotate(n=Count("id")))
    profile = request.user.profile
    recs = recommend(profile.research_interests, limit=4) if profile.interest_keywords else []
    target_count = bookmarks_for(request).filter(is_starred=True).count()
    checklist = [
        ("Add research interests", bool(profile.interest_keywords), reverse("accounts:profile")),
        ("Star a target venue", target_count > 0, reverse("venues:list")),
        ("Track a submission", request.user.submissions.exists(), reverse("tracker:create")),
        ("Subscribe to your calendar feed", profile.calendar_subscribed, reverse("accounts:profile") + "#calendar"),
    ]
    return render(
        request,
        "accounts/dashboard.html",
        {
            "cycles": cycles,
            "submissions": subs,
            "status_counts": status_counts,
            "notifications": request.user.notifications.filter(read_at__isnull=True)[:5],
            "lists": request.user.venue_lists.annotate(n=Count("venues")),
            "saved_searches": request.user.saved_searches.all(),
            "recs": recs,
            "target_count": target_count,
            "onboarding": checklist,
            "onboarding_done": all(done for _, done, _ in checklist),
            "calendar_url": request.build_absolute_uri(reverse("accounts:calendar_feed", args=[profile.calendar_token])),
        },
    )


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved.")
        return redirect("accounts:profile")
    p = request.user.profile
    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "profile": p,
            "calendar_url": request.build_absolute_uri(reverse("accounts:calendar_feed", args=[p.calendar_token])),
        },
    )


@login_required
@require_POST
def regenerate_token(request, which):
    if which not in ("calendar", "api"):
        raise Http404
    request.user.profile.regenerate_tokens(calendar=which == "calendar", api=which == "api")
    messages.success(request, f"New {which} token generated; the old one no longer works.")
    return redirect("accounts:profile")


@login_required
@require_POST
def set_timezone(request):
    zone = request.POST.get("timezone", "")
    if zone not in available_timezones():
        return JsonResponse({"error": "Unknown timezone."}, status=400)
    profile = request.user.profile
    profile.timezone = zone
    profile.save(update_fields=["timezone"])
    return JsonResponse({"timezone": zone})


# ------------------------------------------------------------------ email verification
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
@require_POST
@ratelimit("verify_email")
def resend_verification(request):
    if request.user.profile.email_verified:
        messages.success(request, "Your email address is already confirmed.")
    elif send_verification_email(request.user, request):
        messages.success(request, f"We sent a new confirmation link to {request.user.email}.")
    else:
        messages.error(request, "Add an email address in account settings first.")
    return redirect(_safe_next(request, reverse("accounts:dashboard")))


# ------------------------------------------------------------------ account settings
@login_required
def account_settings(request):
    email_form = EmailChangeForm(request.POST or None, user=request.user, initial={"email": request.user.email})
    if request.method == "POST" and email_form.is_valid():
        changed = email_form.cleaned_data["email"] != request.user.email.lower()
        request.user.email = email_form.cleaned_data["email"]
        request.user.save(update_fields=["email"])
        if changed:
            send_verification_email(request.user, request)
            messages.success(request, f"Email address updated — please confirm it via the link we sent to {request.user.email}.")
        else:
            messages.success(request, "Email address unchanged.")
        return redirect("accounts:settings")
    return render(request, "accounts/settings.html", {"email_form": email_form, "delete_form": DeleteAccountForm(user=request.user)})


@login_required
@require_POST
def delete_account(request):
    form = DeleteAccountForm(request.POST, user=request.user)
    if not form.is_valid():
        email_form = EmailChangeForm(user=request.user, initial={"email": request.user.email})
        return render(request, "accounts/settings.html", {"email_form": email_form, "delete_form": form, "delete_open": True}, status=400)
    user = request.user
    with transaction.atomic():
        logout(request)
        logger.info("Account deleted: %s", user.pk)
        user.delete()
    messages.success(request, "Your account and all associated data were deleted.")
    return redirect("venues:list")


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


# ------------------------------------------------------------------ notifications
@login_required
def notifications(request):
    items = request.user.notifications.select_related("venue")[:100]
    return render(request, "accounts/notifications.html", {"items": items})


@login_required
@require_POST
def notifications_read(request):
    request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    if request.headers.get("HX-Request"):
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    return redirect("accounts:notifications")


# ------------------------------------------------------------------ saved searches
@login_required
@require_POST
def saved_search_create(request):
    form = SavedSearchForm(request.POST)
    if form.is_valid():
        s = form.save(commit=False)
        s.user = request.user
        s.last_count = filter_venues(QueryDict(s.querystring)).count()
        s.save()
        messages.success(request, f"Saved search “{s.name}”.")
    else:
        messages.error(request, "Could not save the search (a name is required).")
    return redirect(f"{reverse('venues:list')}?{request.POST.get('querystring', '')}")


@login_required
@require_POST
def saved_search_delete(request, pk):
    get_object_or_404(SavedSearch, pk=pk, user=request.user).delete()
    messages.success(request, "Saved search deleted.")
    return redirect("accounts:dashboard")


# ------------------------------------------------------------------ venue lists
@login_required
def lists_index(request):
    return render(
        request,
        "accounts/lists.html",
        {
            "lists": request.user.venue_lists.annotate(n=Count("venues")),
            "form": VenueListForm(),
        },
    )


@login_required
@require_POST
def list_create(request):
    form = VenueListForm(request.POST)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        messages.success(request, f"Created list “{obj.name}”.")
        return redirect("accounts:list_detail", slug=obj.slug)
    messages.error(request, "Please give the list a name.")
    return redirect("accounts:lists")


def list_detail(request, slug):
    lst = get_object_or_404(VenueList.objects.select_related("user__profile"), slug=slug)
    owner = request.user.is_authenticated and lst.user_id == request.user.id
    if not (lst.is_public or owner):
        raise Http404
    venues = lst.venues.prefetch_related("cycles", "subfields")
    venues = sorted(venues, key=lambda v: (v.next_deadline is None, v.next_deadline[1] if v.next_deadline else 0))
    return render(
        request,
        "accounts/list_detail.html",
        {
            "lst": lst,
            "venues": venues,
            "owner": owner,
            "starred_ids": starred_ids(request),
            "share_url": request.build_absolute_uri(request.path),
        },
    )


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


@login_required
@require_POST
def list_toggle_venue(request, slug, venue_slug):
    lst = get_object_or_404(VenueList, slug=slug, user=request.user)
    venue = get_object_or_404(Venue, slug=venue_slug)
    if lst.venues.filter(pk=venue.pk).exists():
        lst.venues.remove(venue)
        messages.success(request, f"Removed {venue.acronym} from “{lst.name}”.")
    else:
        lst.venues.add(venue)
        messages.success(request, f"Added {venue.acronym} to “{lst.name}”.")
    return redirect(_safe_next(request, reverse("accounts:list_detail", args=[slug])))


@login_required
@require_POST
def list_update(request, slug):
    lst = get_object_or_404(VenueList, slug=slug, user=request.user)
    if request.POST.get("action") == "delete":
        lst.delete()
        messages.success(request, f"Deleted list “{lst.name}”.")
        return redirect("accounts:lists")
    lst.is_public = request.POST.get("is_public") == "on"
    lst.save(update_fields=["is_public"])
    messages.success(request, "List is now public — anyone with the link can view it." if lst.is_public else "List is now private.")
    return redirect("accounts:list_detail", slug=slug)


# ------------------------------------------------------------------ calendar feed
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
