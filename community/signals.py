from django.db.models.signals import post_init, post_save
from django.dispatch import receiver

from venues.models import DeadlineCycle

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
                DeadlineChange.objects.create(cycle=instance, field=f, old_value=old, new_value=new)
    instance._original = {f: getattr(instance, f) for f in TRACKED}
