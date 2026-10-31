from django.conf import settings
from django.core.exceptions import DisallowedHost


def site_base_url(request=None) -> str:
    """Absolute site root without trailing slash: SITE_URL if configured, else the request's host."""
    configured = getattr(settings, "SITE_URL", "").rstrip("/")
    if configured or request is None:
        return configured or "http://localhost:8000"
    try:
        return request.build_absolute_uri("/").rstrip("/")
    except DisallowedHost:
        return ""


def csp_nonce(request):
    """Template context processor: the per-request CSP nonce for the few inline scripts."""
    return {"csp_nonce": getattr(request, "csp_nonce", "")}
