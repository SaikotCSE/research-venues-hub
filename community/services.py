from django.db.models import Avg, Count, Q


def review_summary(venue):
    """Aggregate community experience for a venue: averages plus the share of decided submissions accepted."""
    agg = venue.reviews.aggregate(
        n=Count("id"),
        rating=Avg("rating"),
        quality=Avg("review_quality"),
        turnaround=Avg("turnaround_days"),
        accepted=Count("id", filter=Q(outcome="accepted")),
        decided=Count("id", filter=~Q(outcome="pending")),
    )
    agg["accept_pct"] = round(100 * agg["accepted"] / agg["decided"]) if agg["decided"] else None
    for key in ("rating", "quality", "turnaround"):
        if agg[key] is not None:
            agg[key] = round(float(agg[key]), 1)
    return agg
