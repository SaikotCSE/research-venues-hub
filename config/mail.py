"""Email backend that sends through Brevo's HTTPS API instead of SMTP.

Some hosts block outbound SMTP: Render's free instances drop ports 25, 465 and 587, which rules out Gmail
SMTP there. This backend talks HTTPS (port 443) instead. Set ``BREVO_API_KEY`` and use a sender address
verified in Brevo (Senders, domains & dedicated IPs → Senders) as ``DJANGO_FROM_EMAIL``.

API reference: https://developers.brevo.com/reference/sendtransacemail
"""

import json
import logging
import urllib.error
import urllib.request
from email.utils import getaddresses, parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger("venuepulse")
ENDPOINT = "https://api.brevo.com/v3/smtp/email"


def _contacts(addresses):
    return [{"email": email, **({"name": name} if name else {})} for name, email in getaddresses(addresses) if email]


class BrevoEmailBackend(BaseEmailBackend):
    def __init__(self, api_key=None, timeout=None, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key or getattr(settings, "BREVO_API_KEY", "")
        self.timeout = timeout or getattr(settings, "EMAIL_TIMEOUT", None) or 15

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            try:
                self._send(message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception("Brevo could not send an email")
        return sent

    def payload(self, message) -> dict:
        name, address = parseaddr(message.from_email)
        body = {
            "sender": {"email": address, **({"name": name} if name else {})},
            "to": _contacts(message.to),
            "subject": message.subject,
            "textContent": message.body,
        }
        if message.cc:
            body["cc"] = _contacts(message.cc)
        if message.bcc:
            body["bcc"] = _contacts(message.bcc)
        if message.reply_to:
            body["replyTo"] = _contacts(message.reply_to[:1])[0]
        for content, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                body["htmlContent"] = content
        if message.attachments:
            raise ValueError("BrevoEmailBackend does not support attachments.")
        return body

    def _send(self, message):
        if not self.api_key:
            raise RuntimeError("BREVO_API_KEY is not set.")
        if not message.recipients():
            return
        request = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(self.payload(message)).encode(),
            headers={"api-key": self.api_key, "Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:300].decode("utf-8", "replace")
            raise RuntimeError(f"Brevo rejected the email (HTTP {exc.code}): {detail}") from None
