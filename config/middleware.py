"""Cross-cutting middleware: request ids and security headers (CSP with per-request nonce)."""
import re
import secrets
import uuid

from django.conf import settings

from config.logging import request_id_var

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestIDMiddleware:
    """Expose ``request.id`` (honouring a sane incoming X-Request-ID) and echo it in the response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        request.id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request.id)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response.setdefault("X-Request-ID", request.id)
        return response


def build_csp(nonce: str) -> str:
    parts = []
    for directive, sources in settings.CSP_DIRECTIVES.items():
        values = [f"'nonce-{nonce}'" if s == "{nonce}" else s for s in sources]
        parts.append(" ".join([directive, *values]))
    return "; ".join(parts)


class SecurityHeadersMiddleware:
    """Adds Content-Security-Policy (nonce-based) and Permissions-Policy headers.

    Templates use ``{{ csp_nonce }}`` on the few inline <script> tags that must run before paint.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        if settings.CSP_ENABLED and "Content-Security-Policy" not in response:
            header = "Content-Security-Policy-Report-Only" if settings.CSP_REPORT_ONLY else "Content-Security-Policy"
            response[header] = build_csp(request.csp_nonce)
        if getattr(settings, "PERMISSIONS_POLICY", ""):
            response.setdefault("Permissions-Policy", settings.PERMISSIONS_POLICY)
        return response
