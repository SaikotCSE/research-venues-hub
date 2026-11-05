import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from venues.models import Venue


def _token():
    return secrets.token_urlsafe(24)


def hash_token(raw: str) -> str:
    """SHA-256 of a personal API token. Tokens are random, so no salt or slow hash is needed."""
    return hashlib.sha256(raw.encode()).hexdigest()


def _hashed_token():
    # A hash of a token nobody knows: the personal API stays locked until an admin issues a token.
    return hash_token(_token())


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=80, blank=True)
    affiliation = models.CharField(max_length=120, blank=True)
    research_interests = models.CharField(max_length=300, blank=True, help_text="Comma-separated keywords used by the recommender.")
    timezone = models.CharField(max_length=64, default="UTC")
    email_reminders = models.BooleanField(default=True)
    weekly_digest = models.BooleanField(default=True, help_text="Weekly email summarising upcoming deadlines for your targets.")
    last_digest_at = models.DateTimeField(null=True, blank=True)
    reminder_days = models.CharField(max_length=40, default="14,7,1", help_text="Days before a deadline to notify, e.g. 14,7,1")
    calendar_token = models.CharField(max_length=64, unique=True, default=_token)
    api_token = models.CharField(
        max_length=64, unique=True, default=_hashed_token, help_text="SHA-256 of the personal API token; the token itself is never stored or shown."
    )
    calendar_subscribed = models.BooleanField(default=False, help_text="Set once the private calendar feed has been fetched.")
    verified_email = models.EmailField(blank=True, help_text="Address confirmed via the verification link; changing the email invalidates it.")

    def __str__(self):
        return f"Profile<{self.user}>"

    @property
    def name(self):
        return self.display_name or self.user.get_username()

    @property
    def email_verified(self) -> bool:
        email = (self.user.email or "").strip().lower()
        return bool(email) and self.verified_email.strip().lower() == email

    @property
    def initials(self):
        parts = [p for p in self.name.replace("_", " ").replace(".", " ").split() if p]
        letters = "".join(p[0] for p in parts[:2]) if len(parts) > 1 else self.name[:2]
        return letters.upper()

    @property
    def reminder_offsets(self):
        out = []
        for part in self.reminder_days.split(","):
            part = part.strip()
            if part.isdigit() and 0 < int(part) <= 365:
                out.append(int(part))
        return sorted(set(out), reverse=True) or [7, 1]

    @property
    def interest_keywords(self):
        return [k.strip().lower() for k in self.research_interests.split(",") if k.strip()]

    def issue_api_token(self) -> str:
        """Replace the personal API token and return the new one. Only its hash is stored, so it can't be shown again."""
        raw = _token()
        self.api_token = hash_token(raw)
        self.save(update_fields=["api_token"])
        return raw


class EmailCode(models.Model):
    """A short-lived one-time code emailed to prove someone controls an address (see accounts/otp.py).

    Only an HMAC of the code is stored. There is at most one live code per (purpose, email): asking again
    replaces it. ``flow`` is a random id also kept in the requesting browser's session, so a code only works
    in the browser that asked for it.
    """

    class Purpose(models.TextChoices):
        SIGNUP = "signup", "Sign-up"
        PASSWORD_RESET = "password_reset", "Password reset"

    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    email = models.EmailField(help_text="Lower-cased address the code was sent to.")
    flow = models.CharField(max_length=64, unique=True)
    code_hash = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True, help_text="Pending sign-up details or the user being reset.")
    attempts = models.PositiveSmallIntegerField(default=0)
    sends = models.PositiveSmallIntegerField(default=1, help_text="Codes sent to this address in the current window.")
    window_started_at = models.DateTimeField()
    sent_at = models.DateTimeField()
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["purpose", "email"], name="uniq_email_code")]
        indexes = [models.Index(fields=["expires_at"])]

    def __str__(self):
        return f"{self.get_purpose_display()} code for {self.email}"


class Notification(models.Model):
    class Kind(models.TextChoices):
        DEADLINE = "deadline", "Deadline reminder"
        CHANGE = "change", "Deadline change"
        SEARCH = "search", "Saved search alert"
        SUBMISSION = "submission", "Submission update"
        SYSTEM = "system", "System"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.SYSTEM)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=300)
    url = models.CharField(max_length=300, blank=True)
    key = models.CharField(max_length=120, help_text="Dedup key so the same reminder is only sent once.")
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "key"], name="uniq_notification_key")]

    def __str__(self):
        return self.message


class SavedSearch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches")
    name = models.CharField(max_length=80)
    querystring = models.CharField(max_length=500, blank=True)
    alert = models.BooleanField(default=False, help_text="Notify me when more venues match this search.")
    last_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class VenueList(models.Model):
    """A named, optionally public/shareable collection of venues."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="venue_lists")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.CharField(max_length=300, blank=True)
    is_public = models.BooleanField(default=False)
    venues = models.ManyToManyField(Venue, related_name="lists", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "list"
            slug = base
            while VenueList.objects.filter(slug=slug).exists():
                slug = f"{base}-{secrets.token_hex(2)}"
            self.slug = slug
        super().save(*args, **kwargs)
