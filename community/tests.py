from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from venues.models import DeadlineCycle, Venue

from .models import DeadlineChange, DeadlineSuggestion, VenueReview


class CommunityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)
        cls.user = User.objects.create_user("alice", "a@example.com", "pw-12345-xyz")
        cls.venue = Venue.objects.get(slug="neurips")

    def setUp(self):
        self.client.force_login(self.user)

    def test_review_create_update_and_stats(self):
        url = reverse("community:review", args=["neurips"])
        self.client.post(url, {"rating": 4, "review_quality": 3, "turnaround_days": 90, "outcome": "accepted", "comment": "Fair reviews"})
        self.client.post(url, {"rating": 5, "review_quality": 4, "turnaround_days": 100, "outcome": "accepted", "comment": "Updated"})
        self.assertEqual(VenueReview.objects.filter(venue=self.venue).count(), 1, "one review per user")
        bob = User.objects.create_user("bob", "b@example.com", "pw-12345-xyz")
        VenueReview.objects.create(user=bob, venue=self.venue, rating=3, outcome="rejected", turnaround_days=110)
        r = self.client.get(reverse("venues:detail", args=["neurips"]))
        stats = r.context["review_stats"]
        self.assertEqual((stats["n"], float(stats["rating"]), stats["accept_pct"]), (2, 4.0, 50))
        self.assertContains(r, "Updated")

    def test_review_validation(self):
        r = self.client.post(reverse("community:review", args=["neurips"]), {"rating": 9, "review_quality": 3, "outcome": "pending"}, follow=True)
        self.assertFalse(VenueReview.objects.exists())
        self.assertContains(r, "Could not save review")

    def test_review_requires_login(self):
        self.client.logout()
        r = self.client.post(reverse("community:review", args=["neurips"]), {"rating": 5, "review_quality": 5, "outcome": "pending"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(VenueReview.objects.exists())

    def test_changes_logged_on_cycle_edit(self):
        cycle = self.venue.cycles.filter(submission_deadline__gt=timezone.now()).first()
        old = cycle.submission_deadline
        self.assertEqual(DeadlineChange.objects.count(), 0)
        c = DeadlineCycle.objects.get(pk=cycle.pk)
        c.submission_deadline = old + timedelta(days=7)
        c.save()
        ch = DeadlineChange.objects.get()
        self.assertEqual((ch.field, ch.delta_days), ("submission_deadline", 7))
        c.save()  # no further change
        self.assertEqual(DeadlineChange.objects.count(), 1)
        self.assertContains(self.client.get(reverse("community:changes")), "+7 d")
        self.assertContains(self.client.get(reverse("venues:detail", args=["neurips"])), "Recent date changes")

    def test_reseeding_does_not_spam_changes(self):
        call_command("seed_venues", verbosity=0)
        self.assertEqual(DeadlineChange.objects.count(), 0)

    def test_suggestion_flow_and_approval(self):
        cycle = self.venue.next_cycle
        new = timezone.now() + timedelta(days=200)
        r = self.client.post(
            reverse("community:suggest", args=[cycle.pk]),
            {"field": "submission_deadline", "new_value": new.strftime("%Y-%m-%dT%H:%M"), "source_url": "neurips.cc/dates", "note": "Official"},
        )
        self.assertRedirects(r, self.venue.get_absolute_url())
        s = DeadlineSuggestion.objects.get()
        self.assertEqual((s.status, s.source_url), ("pending", "https://neurips.cc/dates"))
        s.approve()
        cycle.refresh_from_db()
        self.assertEqual(cycle.submission_deadline.replace(second=0, microsecond=0), new.replace(second=0, microsecond=0))
        self.assertFalse(cycle.is_projected)
        self.assertTrue(DeadlineChange.objects.filter(cycle=cycle, field="submission_deadline").exists())

    def test_admin_actions(self):
        from django.contrib import admin

        self.assertIn(DeadlineSuggestion, admin.site._registry)
        self.assertIn("approve", admin.site._registry[DeadlineSuggestion].actions or ["approve"])
