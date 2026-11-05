"""One-time codes emailed to prove someone controls an address (sign-up and password reset).

``issue()`` stores an HMAC of a fresh 6-digit code and remembers the flow id in the session; the caller emails
the code with ``send_code_email()``. ``verify()`` checks a submitted code for the session's flow and counts
wrong guesses; ``finish()`` deletes the code once it has been used.

Limits are per address and kept in the database, so they hold across server processes:

* a code expires after ``CODE_TTL`` and allows ``MAX_ATTEMPTS`` wrong guesses;
* another code can be requested after ``RESEND_COOLDOWN``, at most ``MAX_SENDS`` times per ``SEND_WINDOW``.

That caps guessing at 25 tries an hour against a one-in-a-million code.
"""

import logging
import math
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import EmailCode

logger = logging.getLogger("venuepulse")

Purpose = EmailCode.Purpose

CODE_LENGTH = 6
CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)
SEND_WINDOW = timedelta(hours=1)
MAX_SENDS = 5
SALT = "venuepulse.email-code"

SUBJECTS = {
    Purpose.SIGNUP: "{code} is your VenuePulse confirmation code",
    Purpose.PASSWORD_RESET: "{code} is your VenuePulse password reset code",
}


class CodeError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


def session_key(purpose) -> str:
    return f"_email_code_{purpose}"


def _digest(flow: str, code: str) -> str:
    return salted_hmac(SALT, f"{flow}:{code}", algorithm="sha256").hexdigest()


def _seconds(delta: timedelta) -> int:
    return max(1, math.ceil(delta.total_seconds()))


def issue(request, purpose, email: str, payload: dict) -> tuple[EmailCode, str]:
    """Create (or replace) the code for ``email`` and bind it to this browser's session.

    Returns the row and the plain code, which only ever goes into the email. Raises :class:`CodeError`
    (status 429) while the address is cooling down or has had too many codes.
    """
    now = timezone.now()
    email = email.strip().lower()
    EmailCode.objects.filter(expires_at__lt=now - SEND_WINDOW).delete()  # housekeeping
    try:
        with transaction.atomic():
            row = EmailCode.objects.select_for_update().filter(purpose=purpose, email=email).first()
            if row is None:
                row = EmailCode(purpose=purpose, email=email, sends=0, window_started_at=now)
            else:
                wait = row.sent_at + RESEND_COOLDOWN - now
                if wait > timedelta(0):
                    raise CodeError(f"Please wait {_seconds(wait)} seconds before requesting another code.", 429)
                if now - row.window_started_at >= SEND_WINDOW:
                    row.sends, row.window_started_at = 0, now
                elif row.sends >= MAX_SENDS:
                    minutes = math.ceil(_seconds(row.window_started_at + SEND_WINDOW - now) / 60)
                    raise CodeError(f"Too many codes were requested for this address. Try again in {minutes} minutes.", 429)
            code = f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"
            row.flow = secrets.token_urlsafe(32)
            row.code_hash = _digest(row.flow, code)
            row.payload = payload
            row.attempts = 0
            row.sends += 1
            row.sent_at = now
            row.expires_at = now + CODE_TTL
            row.save()
    except IntegrityError:  # two requests for the same address at the same moment
        raise CodeError("Please wait a moment before requesting another code.", 429) from None
    request.session[session_key(purpose)] = row.flow
    return row, code


def pending(request, purpose) -> EmailCode | None:
    """The code this browser asked for (possibly expired, so it can be re-sent), if any."""
    flow = request.session.get(session_key(purpose))
    return EmailCode.objects.filter(purpose=purpose, flow=flow).first() if flow else None


def verify(request, purpose, code) -> EmailCode:
    """Return the session's code row if ``code`` matches; otherwise count the attempt and raise CodeError."""
    code = "".join(ch for ch in str(code or "") if not ch.isspace() and ch != "-")
    if not (len(code) == CODE_LENGTH and code.isascii() and code.isdigit()):
        raise CodeError(f"Enter the {CODE_LENGTH}-digit code from the email.")
    flow = request.session.get(session_key(purpose))
    error = None
    with transaction.atomic():
        row = EmailCode.objects.select_for_update().filter(purpose=purpose, flow=flow).first() if flow else None
        if row is None or row.expires_at <= timezone.now():
            error = "This code has expired. Request a new one."
        elif row.attempts >= MAX_ATTEMPTS:
            error = "Too many incorrect attempts. Request a new code."
        elif not constant_time_compare(row.code_hash, _digest(flow, code)):
            row.attempts += 1
            row.save(update_fields=["attempts"])
            left = MAX_ATTEMPTS - row.attempts
            error = f"That code is incorrect. {left} attempt{'' if left == 1 else 's'} left." if left else "That code is incorrect. Request a new code."
    if error:  # raised outside the transaction so the attempt counter is committed
        raise CodeError(error)
    return row


def finish(request, row: EmailCode) -> None:
    """Forget a code that has been used (or must not be used again)."""
    EmailCode.objects.filter(pk=row.pk).delete()
    request.session.pop(session_key(row.purpose), None)


def send_code_email(row: EmailCode, code: str, *, name: str = "") -> None:
    """Email the code. Raises if the mail backend fails, so callers can decide how to respond."""
    context = {"code": code, "minutes": int(CODE_TTL.total_seconds() // 60), "purpose": row.purpose, "name": name}
    body = render_to_string("accounts/email/code.txt", context)
    send_mail(SUBJECTS[row.purpose].format(code=code), body, settings.DEFAULT_FROM_EMAIL, [row.email], fail_silently=False)
    logger.info("Sent a %s code (row %s)", row.purpose, row.pk)
