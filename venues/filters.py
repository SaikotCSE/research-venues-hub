"""QuerySet filtering / sorting shared by the HTML views, JSON API and exports."""
from decimal import Decimal, InvalidOperation

from django.db.models import Case, Exists, F, IntegerField, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Greatest
from django.utils import timezone

from .models import DeadlineCycle, Venue

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


def _list(params, key):
    return [v for v in params.getlist(key) if v]


def _decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def with_annotations(qs, now=None):
    now = now or timezone.now()
    next_dl = (
        DeadlineCycle.objects.filter(venue=OuterRef("pk"), submission_deadline__gte=now)
        .order_by("submission_deadline")
        .values("submission_deadline")[:1]
    )
    core = Case(
        When(core_rank="A*", then=Value(5)), When(core_rank="A", then=Value(4)),
        When(core_rank="B", then=Value(3)), When(core_rank="C", then=Value(2)),
        default=Value(0), output_field=IntegerField(),
    )
    ccf = Case(
        When(ccf_rank="A", then=Value(5)), When(ccf_rank="B", then=Value(3)),
        When(ccf_rank="C", then=Value(2)), default=Value(0), output_field=IntegerField(),
    )
    quart = Case(
        When(quartile="Q1", then=Value(5)), When(quartile="Q2", then=Value(4)),
        When(quartile="Q3", then=Value(3)), When(quartile="Q4", then=Value(2)),
        default=Value(0), output_field=IntegerField(),
    )
    return qs.annotate(next_dl=Subquery(next_dl), rank_score=Greatest(core, ccf, quart))


def filter_venues(params, base=None, now=None):
    """Apply every facet found in ``params`` (a QueryDict or dict-like with getlist/get)."""
    now = now or timezone.now()
    qs = with_annotations(base if base is not None else Venue.objects.all(), now)

    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(acronym__icontains=q) | Q(description__icontains=q)
            | Q(primary_domain__icontains=q) | Q(publisher__icontains=q)
            | Q(subfields__name__icontains=q)
        ).distinct()

    simple = {
        "type": "venue_type__in", "domain": "primary_domain__in", "core": "core_rank__in",
        "ccf": "ccf_rank__in", "quartile": "quartile__in", "country": "country__in",
        "continent": "continent__in", "review": "review_process__in", "publisher": "publisher__in",
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
        "deadline": "next_dl", "impact_factor": "impact_factor", "acceptance_rate": "acceptance_rate",
        "h5_index": "h5_index", "rank": "rank_score", "name": "acronym",
    }[sort]
    expr = F(field).asc(nulls_last=True) if direction == "asc" else F(field).desc(nulls_last=True)
    return qs.order_by(expr, "acronym")


def facet_options():
    """Distinct values used to render the filter sidebar."""
    from django.db.models import Count

    from .models import ResearchSubfield

    venues = Venue.objects
    distinct = lambda f: list(venues.exclude(**{f: ""}).order_by(f).values_list(f, flat=True).distinct())
    return {
        "domains": distinct("primary_domain"),
        "countries": distinct("country"),
        "continents": distinct("continent"),
        "tags": sorted(
            ResearchSubfield.objects.annotate(n=Count("venues")).filter(n__gt=0).order_by("-n", "name")[:40],
            key=lambda t: t.name,
        ),
        "type_choices": Venue.VenueType.choices,
        "core_choices": [c for c in Venue.CoreRank.choices],
        "ccf_choices": [c for c in Venue.CcfRank.choices],
        "quartile_choices": Venue.Quartile.choices,
        "review_choices": Venue.ReviewProcess.choices,
        "status_choices": STATUS_OPTIONS,
        "view_tabs": [("grid", "Cards", "layout-grid"), ("table", "Table", "table"), ("calendar", "Calendar", "calendar-days")],
        "sort_options": [(k, v[0]) for k, v in SORT_OPTIONS.items()],
    }
