"""Minimal RFC 5545 iCalendar generator (no third-party dependency)."""
from datetime import date, datetime, timedelta, timezone as dt_timezone

from django.utils import timezone


def _escape(text):
    return str(text).replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")


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
    return dt.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_calendar(venue, cycles, request_host="venuepulse"):
    now = timezone.now()
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//VenuePulse//Deadlines Hub//EN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{_escape(venue.acronym)} deadlines",
    ]
    for cycle in cycles:
        for key, label, value in cycle.milestones():
            uid = f"{venue.slug}-{cycle.year}-{key}@{request_host}"
            summary = f"{venue.acronym} {cycle.year}: {label}"
            desc = f"{venue.name}\\n{label} ({cycle.timezone_label})\\n{venue.official_website}"
            lines += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{_utc(now)}", f"SUMMARY:{_escape(summary)}", f"DESCRIPTION:{desc}"]
            if venue.official_website:
                lines.append(f"URL:{venue.official_website}")
            if isinstance(value, datetime):
                lines += [f"DTSTART:{_utc(value)}", f"DTEND:{_utc(value + timedelta(minutes=30))}"]
                lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_escape(summary)}", "TRIGGER:-P1D", "END:VALARM"]
            else:  # all-day event dates
                end = value + timedelta(days=1)
                lines += [f"DTSTART;VALUE=DATE:{value.strftime('%Y%m%d')}", f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}"]
            lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"
