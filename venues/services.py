"""Catalogue helpers shared by the app API, feeds and exports."""

from collections import OrderedDict
from datetime import date, timedelta

from django.db.models import Count
from django.utils import timezone

from .models import DeadlineCycle, Venue

MAX_COMPARE = 4
RANK_SCORE = {"A*": 5, "A": 4, "B": 3, "C": 2, "Q1": 5, "Q2": 4, "Q3": 3, "Q4": 2}


def base_queryset():
    return Venue.objects.prefetch_related("subfields", "cycles")


def home_stats(now=None):
    now = now or timezone.now()
    return {
        "venues": Venue.objects.count(),
        "open": Venue.objects.filter(cycles__submission_deadline__gte=now, cycles__submission_open_date__lte=now).distinct().count(),
        "closing_30": DeadlineCycle.objects.filter(submission_deadline__gte=now, submission_deadline__lte=now + timedelta(days=30)).count(),
        "countries": Venue.objects.exclude(country__in=["", "Online"]).values("country").distinct().count(),
    }


def calendar_months(venues, now):
    """Group upcoming milestones of the given venues into the next 12 months."""
    months = OrderedDict()
    y, m = now.year, now.month
    for _ in range(12):
        months[(y, m)] = []
        m += 1
        if m == 13:
            y, m = y + 1, 1
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for v in venues:
        for c in v.cycles.all():
            for key, label, dt in c.milestones():
                if key not in ("abstract", "submission", "notification", "camera_ready") or dt < start_of_today:
                    continue
                k = (dt.year, dt.month)
                if k in months:
                    months[k].append({"venue": v, "cycle": c, "label": label, "kind": key, "at": dt})
    out = []
    for (yy, mm), events in months.items():
        events.sort(key=lambda e: e["at"])
        out.append({"year": yy, "month": date(yy, mm, 1), "events": events})
    return out


def related_venues(venue, limit=6):
    """Venues sharing the most subfield tags (ties broken by acronym)."""
    tag_ids = list(venue.subfields.values_list("pk", flat=True))
    if not tag_ids:
        return []
    qs = (
        Venue.objects.filter(subfields__in=tag_ids)
        .exclude(pk=venue.pk)
        .annotate(shared=Count("subfields", distinct=True))
        .prefetch_related("cycles", "subfields")
        .order_by("-shared", "acronym")[:limit]
    )
    return list(qs)


def _best(values, pick):
    """Indices of the best non-null values (max or min); none when fewer than two venues have data or all tie."""
    present = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(present) < 2:
        return set()
    target = (max if pick == "max" else min)(v for _, v in present)
    if all(v == target for _, v in present):
        return set()
    return {i for i, v in present if v == target}


def rank_score(v):
    return max(RANK_SCORE.get(v.core_rank, 0), {"A": 5, "B": 3, "C": 2}.get(v.ccf_rank, 0), RANK_SCORE.get(v.quartile, 0)) or None


def compare_rows(venues):
    """Rows for the comparison table. Each cell is ``{"value", "type", "best"}``; numeric rows flag the best value(s).

    ``type`` tells the client how to render ``value``: text, number, percent, datetime (ISO) or daterange ({start, end}).
    """

    def dt(value):
        return value.isoformat() if value else None

    deadlines = [v.next_deadline[1] if v.next_deadline else None for v in venues]
    cycles = [v.next_cycle for v in venues]
    spec = [
        ("Type", "text", [v.venue_type for v in venues], None, None),
        ("Domain", "text", [v.primary_domain for v in venues], None, None),
        ("Rank", "text", [v.rank_label for v in venues], [rank_score(v) for v in venues], "max"),
        ("h5-index", "number", [v.h5_index for v in venues], [v.h5_index for v in venues], "max"),
        (
            "Impact factor",
            "number",
            [float(v.impact_factor) if v.impact_factor is not None else None for v in venues],
            [v.impact_factor for v in venues],
            "max",
        ),
        (
            "Acceptance rate",
            "percent",
            [float(v.acceptance_rate) if v.acceptance_rate else None for v in venues],
            [v.acceptance_rate for v in venues],
            "min",
        ),
        ("Next deadline", "datetime", [dt(d) for d in deadlines], deadlines, "min"),
        ("Notification", "datetime", [dt(c.notification_date) if c else None for c in cycles], None, None),
        (
            "Event",
            "daterange",
            [
                {"start": c.event_start_date.isoformat(), "end": (c.event_end_date or c.event_start_date).isoformat()} if c and c.event_start_date else None
                for c in cycles
            ],
            None,
            None,
        ),
        ("Page limit", "text", [v.page_limit or None for v in venues], None, None),
        ("Template", "text", [v.formatting_style or None for v in venues], None, None),
        ("Peer review", "text", [v.review_process for v in venues], None, None),
        (
            "Open access",
            "text",
            [("Yes" + (f" · APC ${v.apc_cost_usd:,}" if v.apc_cost_usd else "")) if v.is_open_access else "No" for v in venues],
            None,
            None,
        ),
        ("Location", "text", [" ".join(p for p in (v.country_flag_emoji, ", ".join(x for x in (v.city, v.country) if x)) if p) for v in venues], None, None),
        ("Publisher", "text", [v.publisher or None for v in venues], None, None),
    ]
    rows = []
    for label, kind, values, scores, pick in spec:
        best = _best(scores, pick) if scores else set()
        rows.append(
            {
                "label": label,
                "key": label.lower().replace(" ", "_").replace("-", "_"),
                "type": kind,
                "cells": [{"value": val, "best": i in best} for i, val in enumerate(values)],
            }
        )
    return rows
