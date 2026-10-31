"""Plain-dict serialisation used by the JSON API and exports."""
from decimal import Decimal


def _num(v):
    return float(v) if isinstance(v, Decimal) else v


def _iso(v):
    return v.isoformat() if v else None


def cycle_to_dict(c):
    return {
        "year": c.year,
        "label": str(c),
        "timezone": c.timezone_label,
        "is_projected": c.is_projected,
        "submission_open_date": _iso(c.submission_open_date),
        "abstract_deadline": _iso(c.abstract_deadline),
        "submission_deadline": _iso(c.submission_deadline),
        "notification_date": _iso(c.notification_date),
        "camera_ready_date": _iso(c.camera_ready_date),
        "verified_at": _iso(c.verified_at),
        "source_url": c.source_url,
        "event_start_date": _iso(c.event_start_date),
        "event_end_date": _iso(c.event_end_date),
    }


def venue_to_dict(v, detail=False, request=None):
    nd = v.next_deadline
    path = v.get_absolute_url()
    data = {
        "name": v.name, "acronym": v.acronym, "slug": v.slug, "venue_type": v.venue_type,
        "primary_domain": v.primary_domain, "subfields": [s.name for s in v.subfields.all()],
        "core_rank": v.core_rank, "ccf_rank": v.ccf_rank, "h5_index": v.h5_index, "h5_median": v.h5_median,
        "impact_factor": _num(v.impact_factor), "quartile": v.quartile, "citescore": _num(v.citescore),
        "sjr": _num(v.sjr), "issn": v.issn, "is_rolling_submission": v.is_rolling_submission,
        "city": v.city, "country": v.country, "continent": v.continent,
        "country_flag_emoji": v.country_flag_emoji, "attendance_mode": v.attendance_mode,
        "page_limit": v.page_limit, "formatting_style": v.formatting_style, "template_url": v.template_url,
        "review_process": v.review_process, "is_open_access": v.is_open_access, "apc_cost_usd": v.apc_cost_usd,
        "acceptance_rate": _num(v.acceptance_rate), "publisher": v.publisher,
        "official_website": v.official_website, "submission_portal_url": v.submission_portal_url,
        "deadline_status": v.deadline_status,
        "next_deadline": {"kind": nd[0], "at": _iso(nd[1])} if nd else None,
        "url": request.build_absolute_uri(path) if request is not None else path,
    }
    if detail:
        data.update(
            description=v.description, scope=v.scope,
            cycles=[cycle_to_dict(c) for c in v.cycles.all()],
        )
    return data


CSV_COLUMNS = [
    "acronym", "name", "venue_type", "primary_domain", "subfields", "core_rank", "ccf_rank", "h5_index",
    "impact_factor", "quartile", "citescore", "sjr", "issn", "acceptance_rate", "deadline_status",
    "next_deadline_kind", "next_deadline_utc", "city", "country", "attendance_mode", "page_limit",
    "formatting_style", "review_process", "is_open_access", "apc_cost_usd", "publisher",
    "official_website", "submission_portal_url",
]


def venue_to_csv_row(v):
    d = venue_to_dict(v)
    nd = d["next_deadline"]
    row = dict(d)
    row["subfields"] = "; ".join(d["subfields"])
    row["next_deadline_kind"] = nd["kind"] if nd else ""
    row["next_deadline_utc"] = nd["at"] if nd else ""
    return [("" if row.get(c) is None else row.get(c)) for c in CSV_COLUMNS]
