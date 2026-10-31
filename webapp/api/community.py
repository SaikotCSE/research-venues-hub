"""Community endpoints: venue experience reviews and deadline correction suggestions."""

from django.shortcuts import get_object_or_404

from community.forms import ReviewForm, SuggestionForm
from community.models import DeadlineSuggestion, VenueReview
from community.services import review_summary
from config.ratelimit import ratelimit
from venues.models import DeadlineCycle, Venue

from .base import endpoint, form_error, text
from .catalog import review_payload


@ratelimit("community_write", methods=("PUT", "DELETE"))
@endpoint("PUT", "DELETE", login=True)
def review(request, slug):
    """Create/replace (PUT) or remove (DELETE) the caller's review of a venue."""
    venue = get_object_or_404(Venue, slug=slug)
    existing = VenueReview.objects.filter(user=request.user, venue=venue).first()
    if request.method == "DELETE":
        if existing:
            existing.delete()
        return {"review": None, "stats": review_summary(venue)}
    form = ReviewForm(
        data={
            "rating": request.data.get("rating"),
            "review_quality": request.data.get("review_quality", 3),
            "turnaround_days": request.data.get("turnaround_days") or "",
            "outcome": text(request.data, "outcome", 10) or "pending",
            "comment": text(request.data, "comment", 2000),
        },
        instance=existing,
    )
    if not form.is_valid():
        form_error(form)
    r = form.save(commit=False)
    r.user, r.venue = request.user, venue
    r.save()
    return {"review": review_payload(r, request), "stats": review_summary(venue), "message": "Thanks — your experience was recorded."}


@ratelimit("community_write")
@endpoint("POST", login=True)
def suggest(request, cycle_id):
    cycle = get_object_or_404(DeadlineCycle.objects.select_related("venue"), pk=cycle_id)
    form = SuggestionForm(
        data={
            "field": text(request.data, "field", 30),
            "new_value": text(request.data, "new_value", 40),
            "source_url": text(request.data, "source_url", 300),
            "note": text(request.data, "note", 300),
        }
    )
    if not form.is_valid():
        form_error(form)
    s = form.save(commit=False)
    s.user, s.cycle = request.user, cycle
    s.save()
    return {"ok": True, "id": s.id, "message": "Suggestion submitted for moderation. Thank you!"}


@endpoint("GET")
def suggestion_fields(request):
    return {"fields": [{"value": v, "label": label} for v, label in DeadlineSuggestion.FIELD_CHOICES]}
