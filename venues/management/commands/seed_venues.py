"""Idempotent seeding of 100+ research publication venues and their deadline cycles.

Usage:  python manage.py seed_venues [--years-back 1 --years-forward 1] [--reset]

Venue metadata (ranks, h5, impact factors, acceptance rates) is approximate and compiled
from public sources; deadlines for future editions are *projections* extrapolated from the
typical calendar of previous editions (flagged ``is_projected``). Always verify on the
official venue website before submitting.
"""
from datetime import date, datetime, time, timedelta, timezone as dt_tz
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from venues.models import DeadlineCycle, ResearchSubfield, Venue
from venues.seed_data import ALL_VENUES

AOE = dt_tz(timedelta(hours=-12))
# Venues held only in even (0) / odd (1) years.
BIENNIAL = {"ICCV": 1, "ECCV": 0, "SOSP": 1, "IPMI": 1}


def _dec(v):
    return None if v is None else Decimal(str(v))


def _md(md, year, ev_md):
    """Resolve 'MM-DD' for an edition held in ``year``: dates after the event month fall in the prior year."""
    m, d = map(int, md.split("-"))
    em, ed = map(int, ev_md.split("-"))
    return date(year if (m, d) <= (em, ed) else year - 1, m, d)


class Command(BaseCommand):
    help = "Seed (or refresh) the database with 100+ global research publication venues."

    def add_arguments(self, parser):
        parser.add_argument("--years-back", type=int, default=1)
        parser.add_argument("--years-forward", type=int, default=1)
        parser.add_argument("--reset", action="store_true", help="Delete existing venues first.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            Venue.objects.all().delete()
        now = timezone.now()
        created = updated = cycles = 0
        for row in ALL_VENUES:
            venue, was_created = self._upsert_venue(row)
            created += was_created
            updated += not was_created
            if not row["rolling"]:
                for year in range(now.year - opts["years_back"], now.year + opts["years_forward"] + 1):
                    if row["acr"] in BIENNIAL and year % 2 != BIENNIAL[row["acr"]]:
                        continue
                    self._upsert_cycle(venue, row, year, now)
                    cycles += 1
        if opts["verbosity"] > 0:
            self.stdout.write(self.style.SUCCESS(
            f"Seeded {created + updated} venues ({created} created, {updated} updated) and {cycles} deadline cycles; "
            f"{Venue.objects.count()} venues in database."))

    def _upsert_venue(self, r):
        scope = f"Topics: {', '.join(r['tags'])}."
        if r["rolling"]:
            scope += " Manuscripts are accepted on a rolling basis throughout the year."
        else:
            scope += " Host city shown is the most recent known edition; locations rotate between editions."
        defaults = dict(
            name=r["name"], acronym=r["acr"], venue_type=r["type"], description=r["desc"], scope=scope,
            primary_domain=r["domain"], core_rank=r["core"], ccf_rank=r["ccf"], h5_index=r["h5"], h5_median=r["h5m"],
            impact_factor=_dec(r["IF"]), quartile=r["quartile"], citescore=_dec(r["citescore"]), sjr=_dec(r["sjr"]),
            issn=r["issn"], is_rolling_submission=r["rolling"], city=r["city"], country=r["country"],
            continent=r["continent"], country_flag_emoji=r["flag"], attendance_mode=r["mode"],
            page_limit=r["pages"], formatting_style=r["style"], template_url=r["template_url"],
            review_process=r["review"], is_open_access=r["oa"], apc_cost_usd=r["apc"] or None,
            acceptance_rate=_dec(r["acc"]), publisher=r["pub"], official_website=r["url"],
            submission_portal_url=r["portal"],
        )
        venue, created = Venue.objects.update_or_create(slug=slugify(r["acr"]), defaults=defaults)
        tags = [ResearchSubfield.objects.get_or_create(slug=slugify(t), defaults={"name": t})[0] for t in r["tags"]]
        venue.subfields.set(tags)
        return venue, created

    def _upsert_cycle(self, venue, r, year, now):
        tz = AOE if r["tz"] == "AoE" else dt_tz.utc
        end_of_day = time(23, 59)

        def at(md):
            return datetime.combine(_md(md, year, r["ev"]), end_of_day, tzinfo=tz) if md else None

        submission = at(r["sub"])
        ev_start = date(year, *map(int, r["ev"].split("-")))
        DeadlineCycle.objects.update_or_create(
            venue=venue, year=year,
            defaults=dict(
                label=f"{venue.acronym} {year}", timezone_label=r["tz"],
                submission_open_date=submission - timedelta(days=r["open_days"]),
                abstract_deadline=at(r["abs"]), submission_deadline=submission,
                notification_date=at(r["notif"]), camera_ready_date=at(r["cam"]),
                event_start_date=ev_start, event_end_date=ev_start + timedelta(days=max(r["days"] - 1, 0)),
                is_projected=submission >= now,
            ),
        )
