"""Minimal RFC 5545 iCalendar generator (no third-party dependency)."""

from datetime import UTC, datetime, timedelta

from django.utils import timezone


def _escape(text):
    text = str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return text.replace("\r\n", "\\n").replace("\n", "\\n")


def _fold(line):
    """Fold at 75 octets per RFC 5545."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, current = [], b""
    for ch in line:
        enc = ch.encode("utf-8")
        limit = 75 if not parts else 74
        if len(current) + len(enc) > limit:
            parts.append(current)
            current = b""
        current += enc
    parts.append(current)
    return "\r\n ".join(p.decode("utf-8") for p in parts)


def _utc(dt):
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _build(name, cycles, host):
    now = timezone.now()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//VenuePulse//Deadlines Hub//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(name)}",
    ]
    for cycle in cycles:
        venue = cycle.venue
        for key, label, value in cycle.milestones():
            uid = f"{venue.slug}-{cycle.year}-{key}@{host}"
            summary = f"{venue.acronym} {cycle.year}: {label}"
            desc = f"{_escape(venue.name)}\\n{label} ({cycle.timezone_label})\\n{venue.official_website}"
            lines += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{_utc(now)}", f"SUMMARY:{_escape(summary)}", f"DESCRIPTION:{desc}"]
            if venue.official_website:
                lines.append(f"URL:{venue.official_website}")
            if isinstance(value, datetime):
                lines += [f"DTSTART:{_utc(value)}", f"DTEND:{_utc(value + timedelta(minutes=30))}"]
                lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_escape(summary)}", "TRIGGER:-P1D", "END:VALARM"]
            else:  # all-day event dates
                lines += [f"DTSTART;VALUE=DATE:{value.strftime('%Y%m%d')}", f"DTEND;VALUE=DATE:{(value + timedelta(days=1)).strftime('%Y%m%d')}"]
            lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def build_calendar(venue, cycles, request_host="venuepulse"):
    return _build(f"{venue.acronym} deadlines", cycles, request_host)


def build_multi_calendar(name, cycles, request_host="venuepulse"):
    """Calendar for many venues; ``cycles`` should be select_related('venue')."""
    return _build(name, cycles, request_host)
