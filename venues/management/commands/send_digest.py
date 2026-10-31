"""Weekly email digest: upcoming deadlines for each user's starred venues and active submissions.

python manage.py send_digest            # send to everyone who opted in
python manage.py send_digest --if-due   # only users whose last digest is ≥ 7 days old (safe to run hourly)
python manage.py send_digest --user alice --dry-run
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.context_processors import site_base_url
from tracker.models import Submission
from venues.models import DeadlineCycle, VenueBookmark

logger = logging.getLogger("venuepulse")
HORIZON_DAYS = 30


def digest_context(user, now=None):
    """Data for one user's digest, or None when there is nothing worth sending."""
    now = now or timezone.now()
    venue_ids = set(VenueBookmark.objects.filter(user=user, is_starred=True).values_list("venue_id", flat=True))
    cycles = list(
        DeadlineCycle.objects.filter(venue_id__in=venue_ids, submission_deadline__gte=now, submission_deadline__lte=now + timedelta(days=HORIZON_DAYS))
        .select_related("venue")
        .order_by("submission_deadline")
    )
    submissions = list(user.submissions.filter(status__in=Submission.ACTIVE).select_related("paper", "venue", "cycle"))
    if not cycles and not submissions:
        return None
    for c in cycles:
        c.days_left = (c.submission_deadline - now).days
    return {"user": user, "cycles": cycles, "submissions": submissions, "site_url": site_base_url(), "horizon": HORIZON_DAYS, "now": now}


class Command(BaseCommand):
    help = "Send the weekly deadline digest email."

    def add_arguments(self, parser):
        parser.add_argument("--if-due", action="store_true", help="Skip users who received a digest in the last 7 days")
        parser.add_argument("--user", help="Only this username")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, if_due=False, user=None, dry_run=False, **options):
        now = timezone.now()
        users = get_user_model().objects.filter(is_active=True, profile__weekly_digest=True).exclude(email="").select_related("profile")
        if user:
            users = users.filter(username=user)
        if if_due:
            users = users.exclude(profile__last_digest_at__gt=now - timedelta(days=7))
        sent = skipped = 0
        for u in users:
            ctx = digest_context(u, now)
            if ctx is None:
                skipped += 1
                continue
            subject = f"VenuePulse weekly: {len(ctx['cycles'])} deadline(s) in the next {HORIZON_DAYS} days"
            if dry_run:
                self.stdout.write(f"[dry-run] {u.get_username()}: {subject}")
                sent += 1
                continue
            message = EmailMultiAlternatives(subject, render_to_string("accounts/email/digest.txt", ctx), settings.DEFAULT_FROM_EMAIL, [u.email])
            message.attach_alternative(render_to_string("accounts/email/digest.html", ctx), "text/html")
            message.send(fail_silently=False)
            u.profile.last_digest_at = now
            u.profile.save(update_fields=["last_digest_at"])
            sent += 1
        logger.info("Digest run: %s sent, %s skipped", sent, skipped)
        self.stdout.write(self.style.SUCCESS(f"{sent} digest(s) {'would be ' if dry_run else ''}sent, {skipped} user(s) with nothing to report."))
