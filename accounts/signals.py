from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from venues.models import VenueBookmark

from .models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(user_logged_in)
def merge_anonymous_bookmarks(sender, request, user, **kwargs):
    """Adopt bookmarks made while browsing anonymously (kept in the session's anon_id)."""
    anon = request.session.get("anon_id") if request else None
    if not anon:
        return
    for bm in VenueBookmark.objects.filter(user__isnull=True, anon_key=anon):
        mine, created = VenueBookmark.objects.get_or_create(user=user, venue=bm.venue, defaults={"is_starred": bm.is_starred, "note": bm.note})
        if not created:
            mine.is_starred = mine.is_starred or bm.is_starred
            mine.note = mine.note or bm.note
            mine.save()
        bm.delete()
