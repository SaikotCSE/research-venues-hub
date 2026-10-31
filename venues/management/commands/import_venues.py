"""Import or update venues (and their deadline cycles) from CSV or JSON.

Accepted formats are exactly what VenuePulse exports, so data can round-trip between instances:

    python manage.py import_venues venues.json            # /export/json/ format (or a plain list)
    python manage.py import_venues venues.csv --dry-run   # /export/csv/ format
    cat venues.json | python manage.py import_venues - --format json

Rows are matched on ``slug`` (derived from the acronym when missing). Unknown columns are ignored;
invalid rows are reported and skipped. ``--dry-run`` validates everything and rolls back.
"""
import csv
import io
import json
import sys
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.text import slugify

from venues.models import DeadlineCycle, ResearchSubfield, Venue

TEXT_FIELDS = [
    "name", "acronym", "venue_type", "description", "scope", "primary_domain", "core_rank", "ccf_rank", "quartile", "issn",
    "city", "country", "continent", "country_flag_emoji", "attendance_mode", "page_limit", "formatting_style", "template_url",
    "review_process", "publisher", "official_website", "submission_portal_url",
]
INT_FIELDS = ["h5_index", "h5_median", "apc_cost_usd"]
DECIMAL_FIELDS = ["impact_factor", "citescore", "sjr", "acceptance_rate"]
BOOL_FIELDS = ["is_rolling_submission", "is_open_access"]
CYCLE_DATETIMES = ["submission_open_date", "abstract_deadline", "submission_deadline", "notification_date", "camera_ready_date"]
CYCLE_DATES = ["event_start_date", "event_end_date"]


class RowError(Exception):
    pass


def _bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(value):
    if value in (None, ""):
        return None
    try:
        return int(Decimal(str(value)))
    except (InvalidOperation, ValueError) as exc:
        raise RowError(f"not a number: {value!r}") from exc


def _decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise RowError(f"not a decimal: {value!r}") from exc


class Command(BaseCommand):
    help = "Import or update venues and deadline cycles from a CSV or JSON file (VenuePulse export format)."

    def add_arguments(self, parser):
        parser.add_argument("path", help="File path, or - for stdin")
        parser.add_argument("--format", choices=["csv", "json"], help="Defaults to the file extension")
        parser.add_argument("--dry-run", action="store_true", help="Validate and report without saving anything")

    def handle(self, *args, path, format=None, dry_run=False, **options):
        fmt = format or ("json" if path.endswith(".json") else "csv" if path.endswith(".csv") else None)
        if fmt is None:
            raise CommandError("Cannot infer the format; pass --format csv|json.")
        try:
            raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8-sig").read()  # noqa: SIM115
        except OSError as exc:
            raise CommandError(f"Cannot read {path}: {exc}") from exc
        rows = self._parse(raw, fmt)

        stats = {"created": 0, "updated": 0, "cycles": 0, "errors": 0}
        with transaction.atomic():
            for index, row in enumerate(rows, start=1):
                label = row.get("acronym") or row.get("slug") or f"row {index}"
                try:
                    with transaction.atomic():
                        created, cycles = self._import_row(row)
                except (RowError, ValidationError, ValueError, TypeError) as exc:
                    stats["errors"] += 1
                    self.stderr.write(self.style.ERROR(f"{label}: {exc}"))
                    continue
                stats["created" if created else "updated"] += 1
                stats["cycles"] += cycles
            if dry_run:
                transaction.set_rollback(True)

        prefix = "[dry-run] " if dry_run else ""
        summary = (f"{prefix}{stats['created']} created, {stats['updated']} updated, "
                   f"{stats['cycles']} cycle(s) upserted, {stats['errors']} error(s).")
        self.stdout.write(self.style.WARNING(summary) if stats["errors"] else self.style.SUCCESS(summary))
        if stats["errors"] and not dry_run:
            raise CommandError("Some rows could not be imported (see errors above).")

    def _parse(self, raw, fmt):
        if fmt == "json":
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise CommandError(f"Invalid JSON: {exc}") from exc
            rows = data.get("results") if isinstance(data, dict) else data
            if not isinstance(rows, list):
                raise CommandError("JSON must be a list of venues or an object with a 'results' list.")
            return rows
        return list(csv.DictReader(io.StringIO(raw)))

    def _import_row(self, row):
        acronym = (row.get("acronym") or "").strip()
        slug = (row.get("slug") or slugify(acronym)).strip()
        if not slug or not (row.get("name") or Venue.objects.filter(slug=slug).exists()):
            raise RowError("needs at least an acronym/slug and a name")
        venue = Venue.objects.filter(slug=slug).first()
        created = venue is None
        venue = venue or Venue(slug=slug)
        for field in TEXT_FIELDS:
            if field in row and row[field] is not None:
                setattr(venue, field, str(row[field]).strip())
        for field in INT_FIELDS:
            if field in row:
                setattr(venue, field, _int(row[field]))
        for field in DECIMAL_FIELDS:
            if field in row:
                setattr(venue, field, _decimal(row[field]))
        for field in BOOL_FIELDS:
            if field in row and row[field] not in (None, ""):
                setattr(venue, field, _bool(row[field]))
        if not venue.acronym:
            venue.acronym = acronym or slug.upper()
        venue.full_clean(exclude=["subfields"])
        venue.save()

        tags = row.get("subfields")
        if tags is not None:
            names = tags if isinstance(tags, list) else [t for t in str(tags).split(";")]
            names = [n.strip() for n in names if n and n.strip()]
            venue.subfields.set([ResearchSubfield.objects.get_or_create(slug=slugify(n), defaults={"name": n})[0] for n in names])

        cycles = 0
        for cycle in row.get("cycles") or []:
            self._import_cycle(venue, cycle)
            cycles += 1
        return created, cycles

    def _import_cycle(self, venue, data):
        try:
            year = int(data["year"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RowError("every cycle needs a numeric 'year'") from exc
        defaults = {}
        for field in CYCLE_DATETIMES:
            if data.get(field):
                value = parse_datetime(str(data[field]))
                if value is None:
                    raise RowError(f"cycle {year}: bad datetime for {field}: {data[field]!r}")
                defaults[field] = value
        for field in CYCLE_DATES:
            if data.get(field):
                value = parse_date(str(data[field]))
                if value is None:
                    raise RowError(f"cycle {year}: bad date for {field}: {data[field]!r}")
                defaults[field] = value
        if "submission_deadline" not in defaults:
            raise RowError(f"cycle {year}: submission_deadline is required")
        if data.get("timezone") in ("AoE", "UTC"):
            defaults["timezone_label"] = data["timezone"]
        if "is_projected" in data:
            defaults["is_projected"] = _bool(data["is_projected"])
        defaults["label"] = data.get("label") or f"{venue.acronym} {year}"
        DeadlineCycle.objects.update_or_create(venue=venue, year=year, defaults=defaults)
