"""Create (or refresh) a demo account that showcases every feature.

    python manage.py seed_demo                    # user "demo" with a random password (printed)
    python manage.py seed_demo --password secret  # fixed password
    python manage.py seed_demo --reset            # wipe the demo user's data first

Requires the catalogue (``seed_venues``) to be loaded. Idempotent.
"""
import secrets

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Notification, SavedSearch, VenueList
from community.models import VenueReview
from tracker.models import Paper, Submission
from venues.models import Venue, VenueBookmark

STARRED = ["neurips", "cvpr", "miccai", "acl", "kdd", "ieee-tmi", "media", "iclr"]
PAPERS = [
    ("Self-supervised 3D segmentation of cardiac MRI", "medical imaging, segmentation, self-supervised", [("miccai", "writing"), ("ieee-tmi", "planning")]),
    ("Sparse mixture-of-experts for long-context language models", "large language models, efficiency", [("iclr", "rejected"), ("neurips", "planning")]),
    ("Graph contrastive learning for fraud detection", "graph learning, data mining", [("kdd", "review")]),
    ("Open-vocabulary detection with vision-language priors", "computer vision, multimodal", [("cvpr", "submitted")]),
]


class Command(BaseCommand):
    help = "Create a demo user with starred venues, papers, submissions, lists, a saved search and reviews."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", help="Defaults to a random password that is printed once")
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, username, password=None, reset=False, **options):
        if not Venue.objects.exists():
            call_command("seed_venues", verbosity=0)
        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com"})
        if reset and not created:
            for qs in (user.papers.all(), user.venue_lists.all(), user.saved_searches.all(), user.venue_reviews.all(), user.notifications.all(),
                       VenueBookmark.objects.filter(user=user)):
                qs.delete()
        password = password or secrets.token_urlsafe(10)
        user.set_password(password)
        user.save()
        profile = user.profile
        profile.display_name = "Dr. Demo Researcher"
        profile.affiliation = "VenuePulse University"
        profile.research_interests = "medical image segmentation, self-supervised learning, large language models, graph learning"
        profile.save()

        venues = {v.slug: v for v in Venue.objects.prefetch_related("cycles")}
        for slug in STARRED:
            if slug in venues:
                VenueBookmark.objects.update_or_create(user=user, venue=venues[slug], defaults={"is_starred": True})
        if "cvpr" in venues:
            VenueBookmark.objects.filter(user=user, venue=venues["cvpr"]).update(note="Rebuttal tip: address reviewer 2's ablation request first.")

        for title, keywords, targets in PAPERS:
            paper, _ = Paper.objects.get_or_create(user=user, title=title, defaults={"keywords": keywords})
            for slug, status in targets:
                venue = venues.get(slug)
                if not venue:
                    continue
                cycle = venue.next_cycle
                if status in ("submitted", "review", "accepted", "rejected"):  # already submitted: attach the latest past cycle
                    past = [c for c in venue.cycles.all() if c.submission_deadline < timezone.now()]
                    cycle = max(past, key=lambda c: c.submission_deadline) if past else cycle
                sub, made = Submission.objects.get_or_create(user=user, paper=paper, venue=venue, defaults={"status": status, "cycle": cycle})
                if made:
                    sub.seed_checklist()
                    for item in sub.checklist_items.all()[: 2 if status == "writing" else 0]:
                        item.done = True
                        item.save(update_fields=["done"])

        lst, _ = VenueList.objects.get_or_create(user=user, name="Medical imaging 2027", defaults={"description": "Where the cardiac MRI paper could go", "is_public": True})
        lst.venues.set([venues[s] for s in ("miccai", "ieee-tmi", "media", "isbi") if s in venues])
        SavedSearch.objects.get_or_create(user=user, name="Open A* calls", defaults={"querystring": "status=open&core=A*", "alert": True})
        if "neurips" in venues:
            VenueReview.objects.update_or_create(user=user, venue=venues["neurips"], defaults={
                "rating": 4, "review_quality": 3, "turnaround_days": 120, "outcome": "accepted",
                "comment": "Thorough reviews; the discussion period genuinely changed one reviewer's mind."})
        Notification.objects.get_or_create(user=user, key="demo:welcome", defaults={
            "kind": "system", "message": "Welcome! This demo account shows targets, a tracker board, lists and reminders.", "url": "/accounts/"})

        self.stdout.write(self.style.SUCCESS(f"Demo account ready: username={username!r} password={password!r}"))
        self.stdout.write(f"Starred {VenueBookmark.objects.filter(user=user, is_starred=True).count()} venues, "
                          f"{user.submissions.count()} submissions, list '{lst.name}' ({lst.venues.count()} venues). "
                          f"Dates as of {timezone.now():%Y-%m-%d}.")
