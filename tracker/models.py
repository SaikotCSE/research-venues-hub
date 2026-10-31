from django.conf import settings
from django.db import models
from django.utils import timezone

from venues.models import DeadlineCycle, Venue


class Paper(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="papers")
    title = models.CharField(max_length=250)
    abstract = models.TextField(blank=True)
    keywords = models.CharField(max_length=300, blank=True, help_text="Comma-separated")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Submission(models.Model):
    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        WRITING = "writing", "Writing"
        SUBMITTED = "submitted", "Submitted"
        REVIEW = "review", "Under review"
        REBUTTAL = "rebuttal", "Rebuttal"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    BOARD_ORDER = ["planning", "writing", "submitted", "review", "rebuttal", "accepted", "rejected"]
    ACTIVE = ["planning", "writing", "submitted", "review", "rebuttal"]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions")
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="submissions")
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="submissions")
    cycle = models.ForeignKey(DeadlineCycle, on_delete=models.SET_NULL, null=True, blank=True, related_name="submissions")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNING, db_index=True)
    submitted_on = models.DateField(null=True, blank=True)
    decision_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.paper} → {self.venue}"

    def save(self, *args, **kwargs):
        today = timezone.localdate()
        if self.status in ("submitted", "review") and not self.submitted_on:
            self.submitted_on = today
        if self.status in ("accepted", "rejected") and not self.decision_on:
            self.decision_on = today
        super().save(*args, **kwargs)

    @property
    def target_deadline(self):
        if self.cycle and self.cycle.submission_deadline >= timezone.now():
            return self.cycle.submission_deadline
        return None

    @property
    def days_to_deadline(self):
        d = self.target_deadline
        return (d - timezone.now()).days if d else None

    @property
    def checklist_progress(self):
        total = self.checklist_items.count()
        done = self.checklist_items.filter(done=True).count()
        return done, total

    def seed_checklist(self):
        """Create checklist items from the venue's formatting rules (once)."""
        if self.checklist_items.exists():
            return
        items = [f"Use template: {self.venue.formatting_style or 'see call for papers'}",
                 f"Respect page limit: {self.venue.page_limit or 'see call for papers'}",
                 "Run spell-check and verify references / BibTeX",
                 "Check figures are legible in grayscale"]
        if self.venue.review_process == Venue.ReviewProcess.DOUBLE_BLIND:
            items.append("Anonymise authors, acknowledgements and self-citations")
        if not self.venue.is_open_access and self.venue.is_journal:
            items.append("Prepare cover letter")
        items += ["Upload supplementary material / code", "Submit before the deadline (check AoE!)"]
        ChecklistItem.objects.bulk_create(ChecklistItem(submission=self, text=t, position=i) for i, t in enumerate(items))


class ChecklistItem(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="checklist_items")
    text = models.CharField(max_length=200)
    done = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
