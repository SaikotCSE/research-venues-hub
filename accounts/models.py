import secrets

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from venues.models import Venue


def _token():
    return secrets.token_urlsafe(24)


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=80, blank=True)
    affiliation = models.CharField(max_length=120, blank=True)
    research_interests = models.CharField(max_length=300, blank=True, help_text="Comma-separated keywords used by the recommender.")
    timezone = models.CharField(max_length=64, default="UTC")
    email_reminders = models.BooleanField(default=True)
    reminder_days = models.CharField(max_length=40, default="14,7,1", help_text="Days before a deadline to notify, e.g. 14,7,1")
    calendar_token = models.CharField(max_length=64, unique=True, default=_token)
    api_token = models.CharField(max_length=64, unique=True, default=_token)

    def __str__(self):
        return f"Profile<{self.user}>"

    @property
    def name(self):
        return self.display_name or self.user.get_username()

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

    def regenerate_tokens(self, calendar=False, api=False):
        if calendar:
            self.calendar_token = _token()
        if api:
            self.api_token = _token()
        self.save()


class Notification(models.Model):
    class Kind(models.TextChoices):
        DEADLINE = "deadline", "Deadline reminder"
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

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "list"
            slug = base
            while VenueList.objects.filter(slug=slug).exists():
                slug = f"{base}-{secrets.token_hex(2)}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
