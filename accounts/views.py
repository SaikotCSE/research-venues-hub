from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from tracker.models import Submission
from venues.filters import filter_venues
from venues.ics import build_calendar
from venues.models import DeadlineCycle, Venue
from venues.ownership import bookmarks_for
from venues.recommend import recommend

from .forms import ProfileForm, SavedSearchForm, SignUpForm, StyledAuthForm, VenueListForm
from .models import Notification, SavedSearch, UserProfile, VenueList


class SignInView(LoginView):
    authentication_form = StyledAuthForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    extra_context = {"title": "Log in", "submit": "Log in"}


def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Welcome to VenuePulse! Set your interests so we can recommend venues.")
        return redirect("accounts:profile")
    return render(request, "accounts/form_page.html", {"form": form, "title": "Create your account", "submit": "Sign up"})


@login_required
def dashboard(request):
    now = timezone.now()
    horizon = now + timedelta(days=120)
    cycles = (DeadlineCycle.objects.filter(
        venue__in=bookmarks_for(request).filter(is_starred=True).values("venue_id"),
        submission_deadline__gte=now, submission_deadline__lte=horizon).select_related("venue").order_by("submission_deadline"))
    subs = request.user.submissions.select_related("paper", "venue", "cycle").filter(status__in=Submission.ACTIVE)
    status_counts = dict(request.user.submissions.values_list("status").annotate(n=Count("id")))
    profile = request.user.profile
    recs = recommend(profile.research_interests, limit=4) if profile.interest_keywords else []
    return render(request, "accounts/dashboard.html", {
        "cycles": cycles, "submissions": subs, "status_counts": status_counts,
        "notifications": request.user.notifications.filter(read_at__isnull=True)[:5],
        "lists": request.user.venue_lists.annotate(n=Count("venues")),
        "saved_searches": request.user.saved_searches.all(),
        "recs": recs, "target_count": bookmarks_for(request).filter(is_starred=True).count(),
        "calendar_url": request.build_absolute_uri(reverse("accounts:calendar_feed", args=[profile.calendar_token])),
    })


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved.")
        return redirect("accounts:profile")
    p = request.user.profile
    return render(request, "accounts/profile.html", {
        "form": form, "profile": p,
        "calendar_url": request.build_absolute_uri(reverse("accounts:calendar_feed", args=[p.calendar_token])),
    })


@login_required
@require_POST
def regenerate_token(request, which):
    if which not in ("calendar", "api"):
        raise Http404
    request.user.profile.regenerate_tokens(calendar=which == "calendar", api=which == "api")
    messages.success(request, f"New {which} token generated; the old one no longer works.")
    return redirect("accounts:profile")


# -------------------------------------------------------------- notifications
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


# -------------------------------------------------------------- saved searches
@login_required
@require_POST
def saved_search_create(request):
    form = SavedSearchForm(request.POST)
    if form.is_valid():
        s = form.save(commit=False)
        s.user = request.user
        s.last_count = filter_venues(_qd(s.querystring)).count()
        s.save()
        messages.success(request, f"Saved search “{s.name}”.")
    else:
        messages.error(request, "Could not save the search (a name is required).")
    return redirect(f"{reverse('venues:list')}?{request.POST.get('querystring', '')}")


def _qd(qs):
    from django.http import QueryDict

    return QueryDict(qs)


@login_required
@require_POST
def saved_search_delete(request, pk):
    get_object_or_404(SavedSearch, pk=pk, user=request.user).delete()
    return redirect("accounts:dashboard")


# -------------------------------------------------------------- venue lists
@login_required
def lists_index(request):
    return render(request, "accounts/lists.html", {
        "lists": request.user.venue_lists.annotate(n=Count("venues")),
        "form": VenueListForm(),
    })


@login_required
@require_POST
def list_create(request):
    form = VenueListForm(request.POST)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        return redirect("accounts:list_detail", slug=obj.slug)
    messages.error(request, "Please give the list a name.")
    return redirect("accounts:lists")


def list_detail(request, slug):
    lst = get_object_or_404(VenueList, slug=slug)
    owner = request.user.is_authenticated and lst.user_id == request.user.id
    if not (lst.is_public or owner):
        raise Http404
    venues = lst.venues.prefetch_related("cycles", "subfields")
    venues = sorted(venues, key=lambda v: (v.next_deadline is None, v.next_deadline[1] if v.next_deadline else 0))
    from venues.ownership import starred_ids

    return render(request, "accounts/list_detail.html", {
        "lst": lst, "venues": venues, "owner": owner, "starred_ids": starred_ids(request),
        "share_url": request.build_absolute_uri(request.path),
    })


@login_required
@require_POST
def list_toggle_venue(request, slug, venue_slug):
    lst = get_object_or_404(VenueList, slug=slug, user=request.user)
    venue = get_object_or_404(Venue, slug=venue_slug)
    if lst.venues.filter(pk=venue.pk).exists():
        lst.venues.remove(venue)
    else:
        lst.venues.add(venue)
    nxt = request.POST.get("next", "")
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = reverse("accounts:list_detail", args=[slug])
    return redirect(nxt)


@login_required
@require_POST
def list_update(request, slug):
    lst = get_object_or_404(VenueList, slug=slug, user=request.user)
    if request.POST.get("action") == "delete":
        lst.delete()
        return redirect("accounts:lists")
    lst.is_public = request.POST.get("is_public") == "on"
    lst.save(update_fields=["is_public"])
    return redirect("accounts:list_detail", slug=slug)


# -------------------------------------------------------------- calendar feed
@require_GET
def calendar_feed(request, token):
    profile = get_object_or_404(UserProfile, calendar_token=token)
    now = timezone.now()
    from venues.models import VenueBookmark

    venue_ids = set(VenueBookmark.objects.filter(user=profile.user, is_starred=True).values_list("venue_id", flat=True))
    venue_ids |= set(profile.user.submissions.filter(status__in=Submission.ACTIVE).values_list("venue_id", flat=True))
    cycles = DeadlineCycle.objects.filter(venue_id__in=venue_ids, submission_deadline__gte=now - timedelta(days=1)).select_related("venue")
    from venues.ics import build_multi_calendar

    body = build_multi_calendar(f"VenuePulse – {profile.name}", cycles, request.get_host().split(":")[0])
    resp = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = 'inline; filename="venuepulse.ics"'
    return resp
