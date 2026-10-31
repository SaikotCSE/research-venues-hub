"""Resolve "who owns this bookmark" for logged-in users and anonymous visitors alike."""
import uuid

from .models import VenueBookmark


def anon_id(request, create=False):
    key = request.session.get("anon_id")
    if not key and create:
        key = request.session["anon_id"] = uuid.uuid4().hex
    return key


def owner_kwargs(request, create=False):
    """Lookup kwargs identifying the caller's bookmarks, or None if there is no owner yet."""
    if request.user.is_authenticated:
        return {"user": request.user}
    key = anon_id(request, create)
    return {"user": None, "anon_key": key} if key else None


def bookmarks_for(request):
    kw = owner_kwargs(request)
    return VenueBookmark.objects.filter(**kw) if kw else VenueBookmark.objects.none()


def starred_ids(request):
    return set(bookmarks_for(request).filter(is_starred=True).values_list("venue_id", flat=True))


def get_or_create_bookmark(request, venue):
    kw = owner_kwargs(request, create=True)
    bm, _ = VenueBookmark.objects.get_or_create(venue=venue, **kw, defaults={"is_starred": False})
    return bm
