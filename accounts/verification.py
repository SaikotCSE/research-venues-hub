"""Email verification with signed, expiring, address-bound tokens (no extra table needed)."""

import logging

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from .context_processors import site_base_url

SALT = "venuepulse.verify-email"
MAX_AGE = 60 * 60 * 24 * 3  # three days
logger = logging.getLogger("venuepulse")


def make_token(user) -> str:
    return signing.dumps({"u": user.pk, "e": user.email.lower()}, salt=SALT)


def read_token(token: str):
    """Return (user_id, email) for a valid token, else None (expired, tampered or malformed)."""
    try:
        data = signing.loads(token, salt=SALT, max_age=MAX_AGE)
        return int(data["u"]), str(data["e"])
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        return None


def send_verification_email(user, request=None) -> bool:
    if not user.email:
        return False
    link = site_base_url(request) + reverse("accounts:verify_email", args=[make_token(user)])
    body = render_to_string("accounts/email/verify_email.txt", {"user": user, "link": link, "days": MAX_AGE // 86400})
    send_mail("Confirm your email for VenuePulse", body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    logger.info("Verification email sent to user %s", user.pk)
    return True
