from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from venues.models import DeadlineCycle, Venue

from .forms import ReviewForm, SuggestionForm
from .models import DeadlineChange, DeadlineSuggestion, VenueReview


def review_summary(venue):
    agg = venue.reviews.aggregate(n=Count("id"), rating=Avg("rating"), quality=Avg("review_quality"), turnaround=Avg("turnaround_days"),
                                  accepted=Count("id", filter=Q(outcome="accepted")), decided=Count("id", filter=~Q(outcome="pending")))
    agg["accept_pct"] = round(100 * agg["accepted"] / agg["decided"]) if agg["decided"] else None
    return agg


@login_required
@require_POST
def review_save(request, slug):
    venue = get_object_or_404(Venue, slug=slug)
    existing = VenueReview.objects.filter(user=request.user, venue=venue).first()
    form = ReviewForm(request.POST, instance=existing)
    if form.is_valid():
        r = form.save(commit=False)
        r.user, r.venue = request.user, venue
        r.save()
        messages.success(request, "Thanks — your experience was recorded.")
    else:
        messages.error(request, "Could not save review: " + "; ".join(sum(form.errors.values(), [])))
    return redirect(venue.get_absolute_url() + "#reviews")


@login_required
def suggest(request, cycle_id):
    cycle = get_object_or_404(DeadlineCycle.objects.select_related("venue"), pk=cycle_id)
    form = SuggestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        s = form.save(commit=False)
        s.user, s.cycle = request.user, cycle
        s.save()
        messages.success(request, "Suggestion submitted for moderation. Thank you!")
        return redirect(cycle.venue.get_absolute_url())
    return render(request, "accounts/form_page.html", {
        "form": form, "title": f"Suggest a correction · {cycle}", "submit": "Submit suggestion",
        "intro": "Times are interpreted as UTC. Include a link to the official call so moderators can verify."})


def changes(request):
    items = DeadlineChange.objects.select_related("cycle__venue").order_by("-changed_at")[:100]
    return render(request, "community/changes.html", {"items": items})
