"""Create in-app notifications (and optional emails) for approaching deadlines and saved-search alerts.

Run periodically (e.g. hourly via cron):  python manage.py send_reminders [--dry-run]
Idempotent: each (user, venue, cycle, milestone, offset) reminder is sent at most once.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.http import QueryDict
from django.urls import reverse
from django.utils import timezone

from accounts.models import Notification
from tracker.models import Submission
from venues.filters import filter_venues
from venues.models import DeadlineCycle, VenueBookmark


class Command(BaseCommand):
    help = "Send deadline reminders and saved-search alerts."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        now = timezone.now()
        created = emails = 0
        for user in get_user_model().objects.select_related("profile").filter(is_active=True):
            profile = user.profile
            offsets = profile.reminder_offsets
            venue_ids = set(VenueBookmark.objects.filter(user=user, is_starred=True).values_list("venue_id", flat=True))
            venue_ids |= set(user.submissions.filter(status__in=["planning", "writing"]).values_list("venue_id", flat=True))
            cycles = DeadlineCycle.objects.filter(venue_id__in=venue_ids, submission_deadline__gte=now,
                                                  submission_deadline__lte=now + timedelta(days=max(offsets) + 1)).select_related("venue")
            fresh = []
            for c in cycles:
                for label, when in (("Abstract", c.abstract_deadline), ("Paper", c.submission_deadline)):
                    if not when or when < now:
                        continue
                    days_left = (when - now).total_seconds() / 86400
                    due = [o for o in offsets if days_left <= o]
                    if not due:
                        continue
                    offset = min(due)  # tightest threshold crossed
                    key = f"deadline:{c.pk}:{label}:{offset}"
                    msg = f"{c.venue.acronym} {c.year} {label.lower()} deadline in {max(int(days_left), 0)} day(s) ({when:%b %d %H:%M} UTC)"
                    fresh.append((key, msg, c.venue))
            for key, msg, venue in fresh:
                if Notification.objects.filter(user=user, key=key).exists():
                    continue
                created += 1
                if opts["dry_run"]:
                    self.stdout.write(f"[dry-run] {user}: {msg}")
                    continue
                Notification.objects.create(user=user, kind="deadline", venue=venue, message=msg, key=key, url=venue.get_absolute_url())
                if profile.email_reminders and user.email:
                    send_mail(f"VenuePulse reminder: {venue.acronym}", f"{msg}\n\n{settings.SITE_URL}{venue.get_absolute_url()}\n",
                              settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
                    emails += 1
            for search in user.saved_searches.filter(alert=True):
                count = filter_venues(QueryDict(search.querystring)).count()
                if count > search.last_count:
                    key = f"search:{search.pk}:{count}"
                    if not opts["dry_run"] and not Notification.objects.filter(user=user, key=key).exists():
                        Notification.objects.create(
                            user=user, kind="search", message=f"Saved search “{search.name}” now matches {count} venues (+{count - search.last_count})",
                            key=key, url=f"{reverse('venues:list')}?{search.querystring}")
                        created += 1
                if not opts["dry_run"]:
                    search.last_count = count
                    search.save(update_fields=["last_count"])
        self.stdout.write(self.style.SUCCESS(f"{created} notification(s) created, {emails} email(s) sent."))
