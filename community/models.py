from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from venues.models import DeadlineCycle, Venue


class VenueReview(models.Model):
    """A community member's experience submitting to a venue."""

    class Outcome(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        PENDING = "pending", "Still pending"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="venue_reviews")
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], help_text="Overall experience, 1-5")
    review_quality = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    turnaround_days = models.PositiveIntegerField(null=True, blank=True, help_text="Days from submission to decision")
    outcome = models.CharField(max_length=10, choices=Outcome.choices, default=Outcome.PENDING)
    comment = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "venue"], name="uniq_review_user_venue")]

    def __str__(self):
        return f"{self.venue} {self.rating}★ by {self.user}"


class DeadlineChange(models.Model):
    """Audit log of changes to a cycle's dates (extensions, shifts)."""

    cycle = models.ForeignKey(DeadlineCycle, on_delete=models.CASCADE, related_name="changes")
    field = models.CharField(max_length=40)
    old_value = models.DateTimeField(null=True)
    new_value = models.DateTimeField(null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.cycle} {self.field}: {self.old_value} → {self.new_value}"

    FIELD_LABELS = {
        "abstract_deadline": "Abstract deadline",
        "submission_deadline": "Paper deadline",
        "notification_date": "Notification",
        "camera_ready_date": "Camera-ready",
    }

    @property
    def field_label(self):
        return self.FIELD_LABELS.get(self.field, self.field)

    @property
    def delta_days(self):
        if self.old_value and self.new_value:
            return (self.new_value - self.old_value).days
        return None


class DeadlineSuggestion(models.Model):
    """User-submitted correction to a venue's data, moderated in the admin."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    FIELD_CHOICES = [
        ("abstract_deadline", "Abstract deadline"),
        ("submission_deadline", "Submission deadline"),
        ("notification_date", "Notification date"),
        ("camera_ready_date", "Camera-ready date"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="suggestions")
    cycle = models.ForeignKey(DeadlineCycle, on_delete=models.CASCADE, related_name="suggestions")
    field = models.CharField(max_length=30, choices=FIELD_CHOICES)
    new_value = models.DateTimeField()
    source_url = models.URLField(blank=True)
    note = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.cycle} {self.field} → {self.new_value:%Y-%m-%d}"

    def approve(self):
        setattr(self.cycle, self.field, self.new_value)
        self.cycle.mark_verified(source_url=self.source_url, save=False)
        self.cycle.save()
        self.status = self.Status.APPROVED
        self.save(update_fields=["status"])
