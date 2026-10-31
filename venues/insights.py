"""Catalogue-wide aggregates behind the Insights page and /api/insights/ (cached per catalogue version)."""
from collections import Counter
from datetime import date, timedelta

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

from .models import DeadlineCycle, Venue, catalog_version


def _compute(now):
    months = []
    y, m = now.year, now.month
    for _ in range(12):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    counts = Counter()
    for dt in DeadlineCycle.objects.filter(submission_deadline__gte=now).values_list("submission_deadline", flat=True):
        counts[(dt.year, dt.month)] += 1
    conf = Venue.objects.exclude(venue_type="Journal")
    journals = Venue.objects.filter(venue_type="Journal")
    scatter = [
        {"x": float(v.acceptance_rate), "y": v.h5_index, "label": v.acronym}
        for v in conf.exclude(acceptance_rate=None).exclude(h5_index=None).only("acronym", "acceptance_rate", "h5_index")
    ]
    core = dict(conf.values_list("core_rank").annotate(n=Count("id")))
    quart = dict(journals.values_list("quartile").annotate(n=Count("id")))
    return {
        "deadlines_by_month": {"labels": [date(y, m, 1).strftime("%b %Y") for y, m in months], "values": [counts[k] for k in months]},
        "by_domain": list(Venue.objects.values_list("primary_domain").annotate(n=Count("id")).order_by("-n")),
        "by_type": list(Venue.objects.values_list("venue_type").annotate(n=Count("id")).order_by("-n")),
        "core_distribution": [[r, core.get(r, 0)] for r in ("A*", "A", "B", "C", "Unranked")],
        "quartile_distribution": [[q, quart.get(q, 0)] for q in ("Q1", "Q2", "Q3", "Q4")],
        "by_continent": list(Venue.objects.exclude(continent="Online").values_list("continent").annotate(n=Count("id")).order_by("-n")),
        "top_impact": [[v.acronym, float(v.impact_factor)] for v in journals.exclude(impact_factor=None).order_by("-impact_factor")[:10]],
        "scatter": scatter,
        "open_access_share": {"open": Venue.objects.filter(is_open_access=True).count(), "closed": Venue.objects.filter(is_open_access=False).count()},
        "totals": {
            "venues": Venue.objects.count(),
            "cycles": DeadlineCycle.objects.count(),
            "upcoming": DeadlineCycle.objects.filter(submission_deadline__gte=now).count(),
            "closing_30d": DeadlineCycle.objects.filter(submission_deadline__gte=now, submission_deadline__lte=now + timedelta(days=30)).count(),
        },
        "generated_at": now.isoformat(),
    }


def insights_data():
    now = timezone.now()
    key = f"insights:{catalog_version()}:{now:%Y%m%d%H}"  # deadlines roll over, so refresh at least hourly
    data = cache.get(key)
    if data is None:
        data = _compute(now)
        cache.set(key, data, 60 * 60)
    return data
