"""Project-specific system checks (run with ``manage.py check --deploy``)."""

from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.security, deploy=True)
def check_site_url(app_configs, **kwargs):
    url = getattr(settings, "SITE_URL", "")
    if not url:
        return [
            Warning(
                "SITE_URL is not set.",
                hint="Set SITE_URL (e.g. https://venuepulse.example.com) so emails, feeds and canonical links use your public domain.",
                id="venuepulse.W001",
            )
        ]
    if not url.startswith("https://"):
        return [Warning("SITE_URL does not use https://.", hint="Serve the site over HTTPS in production.", id="venuepulse.W002")]
    return []


@register(deploy=True)
def check_email_backend(app_configs, **kwargs):
    if settings.EMAIL_BACKEND.endswith((".console.EmailBackend", ".filebased.EmailBackend", ".locmem.EmailBackend", ".dummy.EmailBackend")):
        return [
            Warning(
                "Email is not configured, so nobody can sign up or reset a password (both need an emailed code).",
                hint="Set BREVO_API_KEY (works on hosts that block SMTP, e.g. Render's free plan) or EMAIL_HOST and friends. See docs/DEPLOYMENT.md.",
                id="venuepulse.W003",
            )
        ]
    return []
