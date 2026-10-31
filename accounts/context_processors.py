from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.urls import reverse


def site_base_url(request=None) -> str:
    """Absolute site root without trailing slash: SITE_URL if configured, else the request's host."""
    configured = getattr(settings, "SITE_URL", "").rstrip("/")
    if configured or request is None:
        return configured or "http://localhost:8000"
    try:
        return request.build_absolute_uri("/").rstrip("/")
    except DisallowedHost:
        return ""


def _link(url_name, label, icon, path, exact=False):
    url = reverse(url_name)
    active = path == url if exact or url == "/" else path.startswith(url)
    return {"url": url, "label": label, "icon": icon, "active": active}


def nav(request):
    """Navigation, notification badge, canonical URL and CSP nonce for every template."""
    user = getattr(request, "user", None)
    authed = user is not None and user.is_authenticated
    path = request.path
    nav_links = [
        _link("venues:list", "Explore", "search", path, exact=True),
        _link("venues:recommend", "Recommend", "sparkles", path),
        _link("venues:plan", "Planner", "calendar-days", path),
        _link("venues:insights", "Insights", "chart-bar", path),
        _link("venues:targets", "My Targets", "star", path),
    ]
    if authed:
        nav_links.append(_link("tracker:board", "Tracker", "kanban", path))
    user_links = [
        {"url": reverse("accounts:dashboard"), "label": "Dashboard", "icon": "layout-grid"},
        {"url": reverse("tracker:board"), "label": "Submission tracker", "icon": "kanban"},
        {"url": reverse("tracker:papers"), "label": "My papers", "icon": "file-text"},
        {"url": reverse("accounts:lists"), "label": "My lists", "icon": "list"},
        {"url": reverse("accounts:profile"), "label": "Profile & API", "icon": "user"},
        {"url": reverse("accounts:settings"), "label": "Account settings", "icon": "settings"},
    ]
    site_url = site_base_url(request)
    return {
        "needs_email_verification": authed and bool(user.email) and not user.profile.email_verified,
        "unread_count": user.notifications.filter(read_at__isnull=True).count() if authed else 0,
        "nav_links": nav_links,
        "user_links": user_links,
        "site_url": site_url,
        "canonical_url": site_url + path,
        "csp_nonce": getattr(request, "csp_nonce", ""),
    }
