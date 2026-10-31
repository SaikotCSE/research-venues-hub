"""QuerySet filtering / sorting shared by the HTML views, JSON API and exports."""

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.cache import cache
from django.db.models import Case, Count, Exists, F, IntegerField, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone

from .models import DeadlineCycle, ResearchSubfield, Venue, VenueBookmark, catalog_version

SORT_OPTIONS = {
    # key: (label, default direction)
    "deadline": ("Next deadline", "asc"),
    "impact_factor": ("Impact factor", "desc"),
    "acceptance_rate": ("Acceptance rate", "asc"),
    "h5_index": ("h5-index", "desc"),
    "rank": ("Rank", "desc"),
    "name": ("Name", "asc"),
}

STATUS_OPTIONS = [
    ("upcoming", "Upcoming"),
    ("open", "Open now"),
    ("rolling", "Rolling"),
    ("past", "Past"),
]

WITHIN_OPTIONS = [("7", "7 days"), ("14", "2 weeks"), ("30", "30 days"), ("60", "60 days"), ("90", "90 days")]

VIEW_TABS = [
    ("grid", "Cards", "layout-grid"),
    ("table", "Table", "table"),
    ("timeline", "Timeline", "chart-gantt"),
    ("calendar", "Calendar", "calendar-days"),
]


def _list(params, key):
    return [v for v in params.getlist(key) if v]


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def with_annotations(qs, now=None):
    now = now or timezone.now()
    next_dl = DeadlineCycle.objects.filter(venue=OuterRef("pk"), submission_deadline__gte=now).order_by("submission_deadline").values("submission_deadline")[:1]
    core = Case(
        When(core_rank="A*", then=Value(5)),
        When(core_rank="A", then=Value(4)),
        When(core_rank="B", then=Value(3)),
        When(core_rank="C", then=Value(2)),
        default=Value(0),
        output_field=IntegerField(),
    )
    ccf = Case(
        When(ccf_rank="A", then=Value(5)),
        When(ccf_rank="B", then=Value(3)),
        When(ccf_rank="C", then=Value(2)),
        default=Value(0),
        output_field=IntegerField(),
    )
    quart = Case(
        When(quartile="Q1", then=Value(5)),
        When(quartile="Q2", then=Value(4)),
        When(quartile="Q3", then=Value(3)),
        When(quartile="Q4", then=Value(2)),
        default=Value(0),
        output_field=IntegerField(),
    )
    return qs.annotate(next_dl=Subquery(next_dl), rank_score=Greatest(core, ccf, quart))


def with_tracker_counts(qs):
    """Annotate ``trackers``: how many people starred each venue (social proof)."""
    trackers = VenueBookmark.objects.filter(venue=OuterRef("pk"), is_starred=True).order_by().values("venue").annotate(c=Count("pk")).values("c")
    return qs.annotate(trackers=Coalesce(Subquery(trackers), 0))


def filter_venues(params, base=None, now=None):
    """Apply every facet found in ``params`` (a QueryDict or dict-like with getlist/get)."""
    now = now or timezone.now()
    qs = with_annotations(base if base is not None else Venue.objects.all(), now)

    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(acronym__icontains=q)
            | Q(description__icontains=q)
            | Q(primary_domain__icontains=q)
            | Q(publisher__icontains=q)
            | Q(subfields__name__icontains=q)
        ).distinct()

    simple = {
        "type": "venue_type__in",
        "domain": "primary_domain__in",
        "core": "core_rank__in",
        "ccf": "ccf_rank__in",
        "quartile": "quartile__in",
        "country": "country__in",
        "continent": "continent__in",
        "review": "review_process__in",
        "publisher": "publisher__in",
    }
    for key, lookup in simple.items():
        values = _list(params, key)
        if values:
            qs = qs.filter(**{lookup: values})

    tags = _list(params, "tag")
    if tags:
        qs = qs.filter(pk__in=Venue.subfields.through.objects.filter(researchsubfield__slug__in=tags).values("venue_id"))

    min_if = _decimal(params.get("min_if"))
    if min_if is not None and min_if > 0:
        qs = qs.filter(impact_factor__gte=min_if)

    if params.get("oa") in ("1", "true", "on", "yes"):
        qs = qs.filter(is_open_access=True)

    within = _int(params.get("within"))
    if within and 0 < within <= 3650:
        qs = qs.filter(
            Exists(DeadlineCycle.objects.filter(venue=OuterRef("pk"), submission_deadline__gte=now, submission_deadline__lte=now + timedelta(days=within)))
        )

    cycles = DeadlineCycle.objects.filter(venue=OuterRef("pk"))
    status = params.get("status")
    if status == "rolling":
        qs = qs.filter(is_rolling_submission=True)
    elif status == "open":
        qs = qs.filter(Exists(cycles.filter(Q(submission_open_date__isnull=True) | Q(submission_open_date__lte=now), submission_deadline__gte=now)))
    elif status == "upcoming":
        qs = qs.filter(Exists(cycles.filter(submission_open_date__gt=now)))
    elif status == "past":
        qs = qs.filter(is_rolling_submission=False).exclude(Exists(cycles.filter(submission_deadline__gte=now)))

    return apply_sort(qs, params.get("sort"), params.get("dir"))


def apply_sort(qs, sort, direction):
    sort = sort if sort in SORT_OPTIONS else "deadline"
    direction = direction if direction in ("asc", "desc") else SORT_OPTIONS[sort][1]
    field = {
        "deadline": "next_dl",
        "impact_factor": "impact_factor",
        "acceptance_rate": "acceptance_rate",
        "h5_index": "h5_index",
        "rank": "rank_score",
        "name": "acronym",
    }[sort]
    expr = F(field).asc(nulls_last=True) if direction == "asc" else F(field).desc(nulls_last=True)
    return qs.order_by(expr, "acronym")


def facet_options():
    """Distinct values used to render the filter sidebar (cached; invalidated on catalogue changes)."""
    key = f"facets:{catalog_version()}"
    data = cache.get(key)
    if data is None:

        def distinct(field):
            return list(Venue.objects.exclude(**{field: ""}).order_by(field).values_list(field, flat=True).distinct())

        tags = ResearchSubfield.objects.annotate(n=Count("venues")).filter(n__gt=0).order_by("-n", "name")[:40]
        data = {
            "domains": distinct("primary_domain"),
            "countries": distinct("country"),
            "continents": distinct("continent"),
            "tags": sorted(({"slug": t.slug, "name": t.name, "n": t.n} for t in tags), key=lambda t: t["name"]),
        }
        cache.set(key, data, 60 * 30)
    return {
        **data,
        "type_choices": Venue.VenueType.choices,
        "core_choices": Venue.CoreRank.choices,
        "ccf_choices": Venue.CcfRank.choices,
        "quartile_choices": Venue.Quartile.choices,
        "review_choices": Venue.ReviewProcess.choices,
        "status_choices": STATUS_OPTIONS,
        "within_choices": WITHIN_OPTIONS,
        "view_tabs": VIEW_TABS,
        "sort_options": [(k, v[0]) for k, v in SORT_OPTIONS.items()],
    }


def active_filters(params):
    """Human-readable chips for the filters currently applied: [{name, value, label}]."""
    chips = []
    q = (params.get("q") or "").strip()
    if q:
        chips.append({"name": "q", "value": q, "label": f"“{q}”"})
    status = dict(STATUS_OPTIONS).get(params.get("status") or "")
    if status:
        chips.append({"name": "status", "value": params.get("status"), "label": status})
    within = params.get("within")
    if within and dict(WITHIN_OPTIONS).get(within):
        chips.append({"name": "within", "value": within, "label": f"Closing within {dict(WITHIN_OPTIONS)[within]}"})
    prefixes = {"type": "", "domain": "", "core": "CORE ", "ccf": "CCF ", "quartile": "", "country": "", "continent": "", "review": "", "publisher": ""}
    for name, prefix in prefixes.items():
        for value in _list(params, name):
            chips.append({"name": name, "value": value, "label": f"{prefix}{value}"})
    tags = _list(params, "tag")
    if tags:
        names = dict(ResearchSubfield.objects.filter(slug__in=tags).values_list("slug", "name"))
        chips += [{"name": "tag", "value": t, "label": f"#{names.get(t, t)}"} for t in tags]
    min_if = _decimal(params.get("min_if"))
    if min_if is not None and min_if > 0:
        chips.append({"name": "min_if", "value": params.get("min_if"), "label": f"IF ≥ {min_if.normalize():f}"})
    if params.get("oa") in ("1", "true", "on", "yes"):
        chips.append({"name": "oa", "value": params.get("oa"), "label": "Open access"})
    return chips
