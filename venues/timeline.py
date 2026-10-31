"""Build the data for the Gantt-style "Timeline" view: one row per venue across a 12-month window."""
from datetime import date, timedelta

SEGMENT_STYLES = {
    "open": ("Call for papers open", "bg-sky-400/80 dark:bg-sky-500/70"),
    "review": ("Under review", "bg-amber-400/80 dark:bg-amber-500/70"),
    "camera": ("Camera-ready", "bg-emerald-400/80 dark:bg-emerald-500/70"),
    "event": ("Event", "bg-violet-500 dark:bg-violet-400"),
}


def month_window(today: date, months: int = 12):
    start = today.replace(day=1)
    ticks = []
    y, m = start.year, start.month
    for _ in range(months):
        ticks.append(date(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return start, date(y, m, 1), ticks


def _relevant_cycle(cycles, today: date, window_end: date):
    """Earliest cycle that is still in progress (its event hasn't ended) and starts inside the window."""
    for c in sorted(cycles, key=lambda c: c.submission_deadline):
        last = c.event_end_date or c.event_start_date or c.submission_deadline.date()
        if last >= today and c.submission_deadline.date() < window_end:
            return c
    return None


def timeline_rows(venues, today: date, months: int = 12):
    start, end, ticks = month_window(today, months)
    span = (end - start).days

    def pct(d: date) -> float:
        return round(max(0.0, min(100.0, (d - start).days / span * 100)), 2)

    rows = []
    for v in venues:
        c = _relevant_cycle(v.cycles.all(), today, end)
        if c is None:
            continue
        sub = c.submission_deadline.date()
        notif = c.notification_date.date() if c.notification_date else None
        cam = c.camera_ready_date.date() if c.camera_ready_date else None
        opened = c.submission_open_date.date() if c.submission_open_date else sub - timedelta(days=60)
        spans = [("open", opened, sub), ("review", sub, notif), ("camera", notif, cam)]
        if c.event_start_date:
            spans.append(("event", c.event_start_date, (c.event_end_date or c.event_start_date) + timedelta(days=1)))
        segments = []
        for kind, a, b in spans:
            if not a or not b or b <= start or a >= end or b <= a:
                continue
            left, right = pct(a), pct(b)
            label, css = SEGMENT_STYLES[kind]
            segments.append({"kind": kind, "left": left, "width": max(right - left, 0.6), "label": label, "css": css,
                             "start": a, "end": b - timedelta(days=1) if kind == "event" else b})
        markers = []
        for label, d in (("Abstract deadline", c.abstract_deadline), ("Paper deadline", c.submission_deadline)):
            if d and start <= d.date() < end:
                markers.append({"label": label, "left": pct(d.date()), "at": d})
        parts = [f"paper due {c.submission_deadline:%b %d, %Y}"]
        if notif:
            parts.append(f"notification {notif:%b %d, %Y}")
        if c.event_start_date:
            parts.append(f"event {c.event_start_date:%b %d, %Y}")
        rows.append({
            "venue": v, "cycle": c, "segments": segments, "markers": markers,
            "sort_key": sub if sub >= today else (c.event_start_date or sub),
            "summary": f"{c}: " + "; ".join(parts),
        })
    rows.sort(key=lambda r: (r["sort_key"], r["venue"].acronym))
    return {
        "rows": rows,
        "ticks": [{"left": pct(t), "label": t.strftime("%b"), "year": t.year if t.month == 1 or i == 0 else None} for i, t in enumerate(ticks)],
        "today": pct(today),
        "legend": [(k, *SEGMENT_STYLES[k]) for k in ("open", "review", "camera", "event")],
    }
