"""Calendar deep links and schema.org structured data for venue pages."""
from datetime import UTC, datetime, time, timedelta
from urllib.parse import urlencode

from django.utils import timezone

ATTENDANCE = {
    "In-Person": "https://schema.org/OfflineEventAttendanceMode",
    "Hybrid": "https://schema.org/MixedEventAttendanceMode",
    "Virtual": "https://schema.org/OnlineEventAttendanceMode",
}


def _gcal(dt):
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def calendar_links(venue, cycle, page_url: str) -> dict:
    """Google Calendar / Outlook web links for the cycle's paper deadline (a 30-minute reminder slot)."""
    if cycle is None:
        return {}
    start = cycle.submission_deadline
    end = start + timedelta(minutes=30)
    title = f"{cycle} paper deadline"
    details = f"{venue.name} — paper submission deadline ({cycle.timezone_label}).\n{page_url}"
    google = "https://calendar.google.com/calendar/render?" + urlencode(
        {"action": "TEMPLATE", "text": title, "dates": f"{_gcal(start)}/{_gcal(end)}", "details": details, "location": venue.submission_portal_url or venue.official_website}
    )
    outlook = "https://outlook.live.com/calendar/0/deeplink/compose?" + urlencode(
        {"path": "/calendar/action/compose", "rru": "addevent", "subject": title, "startdt": start.isoformat(), "enddt": end.isoformat(), "body": details}
    )
    return {"google": google, "outlook": outlook}


def milestone_steps(cycle, now=None):
    """Ordered steps of a cycle with state: done / current / upcoming (for the progress stepper)."""
    if cycle is None:
        return []
    now = now or timezone.now()
    raw = [
        ("Call opens", cycle.submission_open_date),
        ("Abstract", cycle.abstract_deadline),
        ("Paper", cycle.submission_deadline),
        ("Notification", cycle.notification_date),
        ("Camera-ready", cycle.camera_ready_date),
        ("Event", cycle.event_start_date),
    ]
    steps, current_found = [], False
    for label, when in raw:
        if not when:
            continue
        moment = when if hasattr(when, "hour") else datetime.combine(when, time.min, tzinfo=UTC)
        done = moment < now
        state = "done" if done else ("upcoming" if current_found else "current")
        current_found = current_found or not done
        steps.append({"label": label, "when": when, "state": state, "is_date": not hasattr(when, "hour")})
    return steps


def structured_data(venue, cycle, page_url: str) -> dict:
    """schema.org JSON-LD: an Event for conferences/workshops, a Periodical for journals."""
    if venue.is_journal:
        data = {
            "@context": "https://schema.org", "@type": "Periodical", "name": venue.name, "alternateName": venue.acronym,
            "url": venue.official_website or page_url, "description": venue.description,
            "publisher": {"@type": "Organization", "name": venue.publisher} if venue.publisher else None,
            "issn": venue.issn or None, "isAccessibleForFree": venue.is_open_access,
        }
    else:
        data = {
            "@context": "https://schema.org", "@type": "Event",
            "name": str(cycle) if cycle else venue.name, "alternateName": venue.acronym,
            "description": venue.description, "url": venue.official_website or page_url,
            "eventAttendanceMode": ATTENDANCE.get(venue.attendance_mode),
            "eventStatus": "https://schema.org/EventScheduled",
            "organizer": {"@type": "Organization", "name": venue.publisher, "url": venue.official_website} if venue.publisher else None,
        }
        if cycle and cycle.event_start_date:
            data["startDate"] = cycle.event_start_date.isoformat()
            data["endDate"] = (cycle.event_end_date or cycle.event_start_date).isoformat()
        if venue.city or venue.country:
            data["location"] = {
                "@type": "Place", "name": ", ".join(p for p in (venue.city, venue.country) if p),
                "address": {"@type": "PostalAddress", "addressLocality": venue.city, "addressCountry": venue.country},
            }
    return {k: v for k, v in data.items() if v not in (None, "")}
