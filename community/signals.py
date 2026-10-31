"""Audit-log every change to a cycle's dates and tell the people tracking that venue."""

from django.db.models.signals import post_init, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from venues.models import DeadlineCycle, VenueBookmark

from .models import DeadlineChange

TRACKED = ("abstract_deadline", "submission_deadline", "notification_date", "camera_ready_date")


@receiver(post_init, sender=DeadlineCycle)
def remember_original(sender, instance, **kwargs):
    instance._original = {f: instance.__dict__.get(f) for f in TRACKED}


@receiver(post_save, sender=DeadlineCycle)
def log_changes(sender, instance, created, **kwargs):
    original = getattr(instance, "_original", {})
    if not created:
        for f in TRACKED:
            old, new = original.get(f), getattr(instance, f)
            if old != new and (old or new):
                change = DeadlineChange.objects.create(cycle=instance, field=f, old_value=old, new_value=new)
                notify_trackers(change)
    instance._original = {f: getattr(instance, f) for f in TRACKED}


def notify_trackers(change):
    """In-app notification for everyone who starred the venue, if the change still matters."""
    from accounts.models import Notification

    now = timezone.now()
    if not any(v and v >= now for v in (change.old_value, change.new_value)):
        return  # a correction to a date in the past is not news
    cycle = change.cycle
    delta = change.delta_days
    if change.old_value and change.new_value:
        verb = "extended" if delta and delta > 0 else "moved earlier" if delta and delta < 0 else "updated"
        detail = f"{change.old_value:%b %d} → {change.new_value:%b %d, %Y}" + (f" ({delta:+d} days)" if delta else "")
    else:
        verb, detail = "updated", (f"{change.new_value:%b %d, %Y}" if change.new_value else "removed")
    message = f"{cycle}: {change.field_label.lower()} {verb} — {detail}"
    user_ids = VenueBookmark.objects.filter(venue_id=cycle.venue_id, is_starred=True, user__isnull=False).values_list("user_id", flat=True)
    url = reverse("venues:detail", args=[cycle.venue.slug])
    Notification.objects.bulk_create(
        [
            Notification(user_id=uid, kind=Notification.Kind.CHANGE, venue_id=cycle.venue_id, message=message[:300], url=url, key=f"change:{change.pk}")
            for uid in user_ids
        ],
        ignore_conflicts=True,
    )
