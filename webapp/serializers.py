"""JSON shapes consumed by the React app (see frontend/src/lib/types.ts for the TypeScript mirror)."""

from decimal import Decimal


def iso(value):
    return value.isoformat() if value else None


def num(value):
    return float(value) if isinstance(value, Decimal) else value


def cycle_payload(c):
    return {
        "id": c.id,
        "year": c.year,
        "label": str(c),
        "timezone": c.timezone_label,
        "is_projected": c.is_projected,
        "verified_at": iso(c.verified_at),
        "source_url": c.source_url,
        "submission_open_date": iso(c.submission_open_date),
        "abstract_deadline": iso(c.abstract_deadline),
        "submission_deadline": iso(c.submission_deadline),
        "notification_date": iso(c.notification_date),
        "camera_ready_date": iso(c.camera_ready_date),
        "event_start_date": iso(c.event_start_date),
        "event_end_date": iso(c.event_end_date),
    }


def venue_ref(v):
    """The few fields needed to link to a venue."""
    return {"slug": v.slug, "acronym": v.acronym, "name": v.name, "flag": v.country_flag_emoji, "venue_type": v.venue_type}


def venue_card(v, starred_ids=frozenset()):
    """Summary used by cards, tables, lists and search results (expects subfields + cycles prefetched)."""
    nd = v.next_deadline
    nc = v.next_cycle
    return {
        **venue_ref(v),
        "primary_domain": v.primary_domain,
        "subfields": [{"slug": s.slug, "name": s.name} for s in v.subfields.all()],
        "rank_label": v.rank_label,
        "core_rank": v.core_rank,
        "ccf_rank": v.ccf_rank,
        "quartile": v.quartile,
        "h5_index": v.h5_index,
        "impact_factor": num(v.impact_factor),
        "acceptance_rate": num(v.acceptance_rate),
        "city": v.city,
        "country": v.country,
        "continent": v.continent,
        "attendance_mode": v.attendance_mode,
        "review_process": v.review_process,
        "is_open_access": v.is_open_access,
        "is_rolling": v.is_rolling_submission,
        "status": v.deadline_status,
        "next_deadline": {"kind": nd[0], "at": iso(nd[1])} if nd else None,
        "next_cycle": cycle_payload(nc) if nc else None,
        "starred": v.id in starred_ids,
        "trackers": getattr(v, "trackers", None),
    }


def submission_payload(s, items=None):
    done, total = items if items is not None else (getattr(s, "items_done", None), getattr(s, "items_total", None))
    if done is None:
        done, total = s.checklist_progress
    cycle = s.cycle
    return {
        "id": s.id,
        "paper": {"id": s.paper_id, "title": s.paper.title},
        "venue": venue_ref(s.venue),
        "cycle": {"id": cycle.id, "year": cycle.year, "label": str(cycle), "submission_deadline": iso(cycle.submission_deadline)} if cycle else None,
        "status": s.status,
        "status_label": s.get_status_display(),
        "submitted_on": iso(s.submitted_on),
        "decision_on": iso(s.decision_on),
        "notes": s.notes,
        "deadline": iso(s.target_deadline),
        "days_left": s.days_to_deadline,
        "checklist": {"done": done, "total": total},
        "created_at": iso(s.created_at),
        "updated_at": iso(s.updated_at),
    }


def notification_payload(n):
    return {
        "id": n.id,
        "kind": n.kind,
        "kind_label": n.get_kind_display(),
        "message": n.message,
        "url": n.url,
        "created_at": iso(n.created_at),
        "read": n.read_at is not None,
    }


def list_payload(lst, count=None):
    return {
        "slug": lst.slug,
        "name": lst.name,
        "description": lst.description,
        "is_public": lst.is_public,
        "count": count if count is not None else getattr(lst, "n", None),
        "created_at": iso(lst.created_at),
    }


def change_payload(ch):
    venue = ch.cycle.venue
    return {
        "id": ch.id,
        "venue": venue_ref(venue),
        "cycle": str(ch.cycle),
        "field": ch.field,
        "field_label": ch.field_label,
        "old_value": iso(ch.old_value),
        "new_value": iso(ch.new_value),
        "delta_days": ch.delta_days,
        "changed_at": iso(ch.changed_at),
    }
