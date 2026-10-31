"""Lightweight, dependency-free venue recommender and deadline planner."""

import re
from datetime import timedelta

from django.utils import timezone

from .filters import with_annotations
from .models import Venue

STOP = set(
    """a an and are as at be by for from has have in into is it its of on or that the their this to we with our
using use based via over under between towards toward new paper method methods approach approaches novel study analysis
can show shows propose proposed present results model models""".split()
)


def tokens(text):
    found = re.findall(r"[a-z0-9][a-z0-9\-\+]+", (text or "").lower())
    return [t for t in found if t not in STOP and not t.isdigit() and (len(t) > 2 or any(c.isdigit() for c in t))]


def recommend(text, *, domain=None, venue_type=None, limit=15, only_with_deadline=False, base=None):
    """Return [{'venue', 'score', 'reasons'}] ranked by topical match, rank and deadline proximity."""
    qtokens = set(tokens(text))
    lowered = (text or "").lower()
    if not qtokens:
        return []
    qs = with_annotations(base if base is not None else Venue.objects.all()).prefetch_related("subfields", "cycles")
    if domain:
        qs = qs.filter(primary_domain=domain)
    if venue_type:
        qs = qs.filter(venue_type=venue_type)
    now = timezone.now()
    results = []
    for v in qs:
        score, reasons = 0.0, []
        for tag in v.subfields.all():
            name = tag.name.lower()
            if name in lowered:
                score += 10
                reasons.append(f"topic “{tag.name}”")
            else:
                overlap = qtokens & set(tokens(name))
                if overlap:
                    score += 4 * len(overlap)
                    reasons.append(f"keyword “{sorted(overlap)[0]}” in tag {tag.name}")
        name_hits = qtokens & set(tokens(f"{v.name} {v.acronym}"))
        if name_hits:
            score += 5 * len(name_hits)
        if v.primary_domain.lower() in lowered or qtokens & set(tokens(v.primary_domain)):
            score += 3
            reasons.append(f"domain {v.primary_domain}")
        desc_hits = qtokens & set(tokens(f"{v.description} {v.scope}"))
        if desc_hits:
            score += min(len(desc_hits), 5)
        if score <= 0:
            continue
        nd = v.next_deadline
        if only_with_deadline and not nd and not v.is_rolling_submission:
            continue
        score *= 1 + (v.rank_score or 0) / 10  # prefer stronger venues among equally relevant ones
        if nd and now <= nd[1] <= now + timedelta(days=120):
            score *= 1.1
        results.append({"venue": v, "score": score, "reasons": list(dict.fromkeys(reasons))[:4], "next": nd})
    results.sort(key=lambda r: -r["score"])
    top = results[:limit]
    if top:
        best = top[0]["score"]
        for r in top:
            r["percent"] = max(1, round(100 * r["score"] / best))
    return top


def plan(ready_date, *, domain=None, venue_type=None, max_months=9, limit=40):
    """Venues with a submission deadline on/after ``ready_date``, soonest first, with slack in days."""
    from .models import DeadlineCycle

    start = ready_date
    end = ready_date + timedelta(days=30 * max_months)
    cycles = (
        DeadlineCycle.objects.filter(submission_deadline__date__gte=start, submission_deadline__date__lte=end)
        .select_related("venue")
        .prefetch_related("venue__subfields")
    )
    if domain:
        cycles = cycles.filter(venue__primary_domain=domain)
    if venue_type:
        cycles = cycles.filter(venue__venue_type=venue_type)
    rows = []
    for c in cycles.order_by("submission_deadline"):
        rows.append({"cycle": c, "venue": c.venue, "slack_days": (c.submission_deadline.date() - ready_date).days})
    return rows[:limit]
