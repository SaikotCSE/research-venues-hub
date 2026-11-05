"""Server side of the single-page app: one HTML shell per route with real titles, SEO metadata and boot data.

Every page URL the React router knows is also a Django URL (keeping the historic URL names, so
``reverse("venues:detail")``, emails and sitemaps keep working). The view decides the HTTP status (404 for a
missing venue, redirects for login-only pages), renders metadata crawlers can read, and embeds the data the
first screen needs so it paints without waiting for an API round trip.
"""

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import Resolver404, resolve
from django.utils.cache import patch_cache_control
from django.utils.dateformat import format as date_format
from django.utils.text import Truncator
from django.views.decorators.csrf import requires_csrf_token
from django.views.decorators.http import require_GET

from accounts.models import VenueList
from config.site import site_base_url
from venues.seo import structured_data
from venues.services import base_queryset

from .api.account import list_detail_payload
from .api.base import error_response
from .api.catalog import calendar_payload, explore_payload, facets_payload, home_payload, timeline_payload, venue_payload
from .api.session import session_payload

SITE_NAME = "VenuePulse"
DEFAULT_DESCRIPTION = "Search, filter, compare and track conference and journal deadlines worldwide, with live countdowns in your timezone and AoE."

# page name -> (title, description, indexable)
PAGES = {
    "explore": ("Conference & journal deadlines with live countdowns", DEFAULT_DESCRIPTION, True),
    "venue_detail": ("Venue", DEFAULT_DESCRIPTION, True),
    "compare": ("Compare venues", "Compare ranks, metrics, deadlines and submission rules of up to four research venues side by side.", True),
    "targets": ("My target venues", "Your starred conferences and journals with live deadline countdowns, notes and exports.", False),
    "recommend": (
        "Venue recommender",
        "Paste your abstract or keywords and get conferences and journals ranked by topical fit, rank and upcoming deadlines.",
        True,
    ),
    "plan": ("Deadline planner", "Tell VenuePulse when your paper will be ready and see every venue you can still make, with the slack in days.", True),
    "insights": (
        "Insights",
        "Charts of the research venue landscape: deadlines by month, ranks, impact factors, acceptance rates and geography.",
        True,
    ),
    "radar": ("Deadline radar", "Every extension and correction to conference and journal deadlines, logged as it happens.", True),
    "about": ("About & FAQ", "How VenuePulse works: AoE deadlines, projected dates, ranks and metrics, reminders and the open data API.", True),
    "privacy": ("Privacy", "What VenuePulse stores about you, why, and how to export or delete it.", True),
    "api_docs": ("API documentation", "JSON API, OpenAPI schema, CSV/JSON exports and iCal/Atom feeds for research venue deadlines.", True),
    "login": ("Log in", "Log in to sync your target venues, reminders and submission tracker.", False),
    "signup": ("Create your account", "Free account: sync starred venues across devices, get deadline reminders and track submissions.", False),
    "password_reset": ("Reset your password", "Get a code by email and choose a new password.", False),
    "password_reset_complete": ("Password updated", "Your password has been reset.", False),
    "password_change": ("Change password", "Change your account password.", False),
    "dashboard": ("Dashboard", "Your deadlines, submissions and alerts at a glance.", False),
    "profile": ("Profile", "Research interests, timezone and reminders.", False),
    "settings": ("Account settings", "Email, password, data export and account deletion.", False),
    "notifications": ("Notifications", "Deadline reminders, change alerts and saved-search matches.", False),
    "lists": ("My lists", "Named, shareable collections of venues.", False),
    "list_detail": ("Venue list", "A shared list of research venues.", True),
    "tracker_board": ("Submission tracker", "Kanban board of your paper submissions.", False),
    "tracker_new": ("Track a submission", "Start tracking a paper submission.", False),
    "tracker_detail": ("Submission", "Status, checklist and notes for a submission.", False),
    "tracker_papers": ("My papers", "Papers you are tracking across venues.", False),
    "not_found": ("Page not found", "The page you are looking for does not exist.", False),
}


# page name -> source module of its lazily loaded chunk (keys of the Vite manifest)
PAGE_MODULES = {
    "explore": "pages/explore.tsx",
    "venue_detail": "pages/venue-detail.tsx",
    "compare": "pages/compare.tsx",
    "targets": "pages/targets.tsx",
    "recommend": "pages/recommend.tsx",
    "plan": "pages/plan.tsx",
    "insights": "pages/insights.tsx",
    "radar": "pages/radar.tsx",
    "about": "pages/about.tsx",
    "privacy": "pages/privacy.tsx",
    "api_docs": "pages/api-docs.tsx",
    "login": "pages/auth/login.tsx",
    "signup": "pages/auth/signup.tsx",
    "password_reset": "pages/auth/password-reset.tsx",
    "password_reset_complete": "pages/auth/password-reset-complete.tsx",
    "password_change": "pages/auth/password-change.tsx",
    "dashboard": "pages/account/dashboard.tsx",
    "profile": "pages/account/profile.tsx",
    "settings": "pages/account/settings.tsx",
    "notifications": "pages/account/notifications.tsx",
    "lists": "pages/account/lists.tsx",
    "list_detail": "pages/account/list-detail.tsx",
    "tracker_board": "pages/tracker/board.tsx",
    "tracker_new": "pages/tracker/new.tsx",
    "tracker_detail": "pages/tracker/detail.tsx",
    "tracker_papers": "pages/tracker/papers.tsx",
}


def _meta(request, page, title=None, description=None, indexable=None, og_type="website", jsonld=()):
    default_title, default_description, default_index = PAGES[page]
    site = site_base_url(request)
    title = title or default_title
    full_title = f"{SITE_NAME} · {title}" if page == "explore" else f"{title} · {SITE_NAME}"
    description = description or default_description
    return {
        "title": full_title,
        "og_title": title if page != "explore" else full_title,
        "description": description,
        "og_description": description,
        "canonical": site + request.path,
        "indexable": default_index if indexable is None else indexable,
        "og_type": og_type,
        "og_image": site + static("venues/img/og-image.jpg"),
        "site_url": site,
        "jsonld": [j for j in jsonld if j],
    }


def render_shell(request, page, *, status=200, meta=None, initial=None, extra=None):
    meta = meta or _meta(request, page)
    boot = {
        "page": page,
        "status": status,
        "session": session_payload(request),
        "initial": initial or {},
        "extra": extra or {},
        "site": {"name": SITE_NAME, "url": meta["site_url"]},
    }
    module = PAGE_MODULES.get(page)
    context = {"meta": meta, "boot": boot, "page": page, "page_module": f"frontend/src/{module}" if module else None}
    response = render(request, "webapp/shell.html", context, status=status)
    patch_cache_control(response, private=True, no_cache=True)
    return response


# ------------------------------------------------------------------ public pages
def simple_page(page):
    @require_GET
    def view(request, **kwargs):
        return render_shell(request, page)

    view.__name__ = f"{page}_page"
    return view


@require_GET
def explore(request):
    view = request.GET.get("view")
    initial = {"facets": facets_payload(), "home": home_payload()}
    if view == "timeline":
        initial["explore"] = timeline_payload(request, request.GET)
    elif view == "calendar":
        initial["explore"] = calendar_payload(request, request.GET)
    else:
        initial["explore"] = explore_payload(request, request.GET)
    meta = _meta(request, "explore")
    meta["canonical"] = meta["site_url"] + "/"  # filtered views share the canonical home page
    return render_shell(request, "explore", meta=meta, initial=initial)


@require_GET
def venue_detail(request, slug):
    venue = base_queryset().filter(slug=slug).first()
    if venue is None:
        return not_found(request, what="venue")
    payload = venue_payload(request, venue)
    cycle = venue.next_cycle
    nd = venue.next_deadline
    when = date_format(nd[1], "M j, Y") if nd else ""
    site = site_base_url(request)
    page_url = site + venue.get_absolute_url()
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Explore", "item": site + "/"},
            {"@type": "ListItem", "position": 2, "name": venue.acronym, "item": page_url},
        ],
    }
    meta = _meta(
        request,
        "venue_detail",
        title=f"{venue.acronym}{f' {cycle.year}' if cycle else ''} deadlines, rank & submission guide",
        description=(
            f"{venue.name} ({venue.acronym}): {f'next {nd[0].lower()} deadline {when}, ' if nd else ''}"
            f"{venue.rank_label}, {venue.page_limit or 'page limit n/a'}, {venue.review_process.lower()} review."
        ),
        og_type="article",
        jsonld=(structured_data(venue, cycle, page_url), breadcrumb),
    )
    meta["og_title"] = f"{venue.acronym} — {venue.name}"
    meta["og_description"] = (f"Next {nd[0].lower()} deadline: {when}. " if nd else "") + Truncator(venue.description).chars(160)
    return render_shell(request, "venue_detail", meta=meta, initial={"venue": payload})


@require_GET
def list_detail(request, slug):
    lst = VenueList.objects.select_related("user__profile").filter(slug=slug).first()
    owner = lst is not None and request.user.is_authenticated and lst.user_id == request.user.id
    if lst is None or not (lst.is_public or owner):
        return not_found(request, what="list")
    meta = _meta(
        request,
        "list_detail",
        title=lst.name,
        description=f"{lst.description or 'A shared list of research venues'} — curated by {lst.user.profile.name} on VenuePulse.",
        indexable=lst.is_public,
    )
    return render_shell(request, "list_detail", meta=meta, initial={"list": list_detail_payload(request, lst, owner)})


# ------------------------------------------------------------------ authentication pages
def guest_page(page):
    """Login/signup/reset pages: signed-in visitors go straight to their dashboard."""

    @require_GET
    def view(request, **kwargs):
        if request.user.is_authenticated and page in ("login", "signup"):
            return redirect("accounts:dashboard")
        return render_shell(request, page)

    view.__name__ = f"{page}_page"
    return view


# ------------------------------------------------------------------ signed-in pages
def private_page(page):
    @require_GET
    def view(request, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return render_shell(request, page)

    view.__name__ = f"{page}_page"
    return view


@require_GET
def submission_detail(request, pk):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if not request.user.submissions.filter(pk=pk).exists():
        return not_found(request, what="submission")
    return render_shell(request, "tracker_detail")


# ------------------------------------------------------------------ errors
def catch_all(request, path=""):
    """Unknown URL: behave like APPEND_SLASH for slash-less paths, else render the app's 404 page.

    (Also used as handler404, so the app's not-found page shows with and without DEBUG.)
    """
    if not request.path.endswith("/") and request.method in ("GET", "HEAD"):
        try:
            match = resolve(request.path + "/")
        except Resolver404:
            match = None
        if match is not None and match.func is not catch_all:
            query = request.META.get("QUERY_STRING", "")
            return redirect(request.path + "/" + (f"?{query}" if query else ""), permanent=True)
    return not_found(request)


def not_found(request, exception=None, what="page"):
    if request.path.startswith("/api/"):
        return error_response("Not found.", 404)
    return render_shell(request, "not_found", status=404, extra={"not_found": what})


@requires_csrf_token
def csrf_failure(request, reason=""):
    if request.path.startswith("/api/"):
        return error_response("CSRF verification failed. Refresh the page and try again.", 403)
    return render(request, "403_csrf.html", {"reason": reason}, status=403)
