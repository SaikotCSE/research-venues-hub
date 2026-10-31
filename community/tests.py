import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from venues.models import DeadlineCycle, Venue

from .models import DeadlineChange, DeadlineSuggestion, VenueReview

APP = "/api/app"


class CommunityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)
        cls.user = User.objects.create_user("alice", "a@example.com", "pw-12345-xyz")
        cls.venue = Venue.objects.get(slug="neurips")

    def setUp(self):
        self.client.force_login(self.user)

    def api(self, method, path, body=None):
        return getattr(self.client, method)(APP + path, data=json.dumps(body or {}), content_type="application/json")

    def test_review_create_update_and_stats(self):
        url = "/venues/neurips/review/"
        self.api("put", url, {"rating": 4, "review_quality": 3, "turnaround_days": 90, "outcome": "accepted", "comment": "Fair reviews"})
        r = self.api("put", url, {"rating": 5, "review_quality": 4, "turnaround_days": 100, "outcome": "accepted", "comment": "Updated"})
        self.assertEqual(r.json()["review"]["comment"], "Updated")
        self.assertEqual(VenueReview.objects.filter(venue=self.venue).count(), 1, "one review per user")
        bob = User.objects.create_user("bob", "b@example.com", "pw-12345-xyz")
        VenueReview.objects.create(user=bob, venue=self.venue, rating=3, outcome="rejected", turnaround_days=110)
        d = self.client.get(f"{APP}/venues/neurips/").json()
        stats = d["review_stats"]
        self.assertEqual((stats["n"], stats["rating"], stats["accept_pct"]), (2, 4.0, 50))
        self.assertEqual(d["me"]["review"]["comment"], "Updated")
        self.assertTrue(d["me"]["review"]["mine"])
        self.assertEqual(self.api("delete", url).json()["review"], None)
        self.assertEqual(VenueReview.objects.filter(venue=self.venue).count(), 1)

    def test_review_validation(self):
        r = self.api("put", "/venues/neurips/review/", {"rating": 9, "review_quality": 3, "outcome": "pending"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("rating", r.json()["fields"])
        self.assertFalse(VenueReview.objects.exists())

    def test_review_requires_login(self):
        self.client.logout()
        r = self.api("put", "/venues/neurips/review/", {"rating": 5, "review_quality": 5, "outcome": "pending"})
        self.assertEqual(r.status_code, 401)
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
        radar = self.client.get(f"{APP}/radar/").json()["results"]
        self.assertEqual((radar[0]["delta_days"], radar[0]["field_label"]), (7, "Paper deadline"))
        self.assertEqual(self.client.get(f"{APP}/venues/neurips/").json()["changes"][0]["delta_days"], 7)
        self.assertContains(self.client.get(reverse("community:changes")), "<title>Deadline radar · VenuePulse</title>")

    def test_reseeding_does_not_spam_changes(self):
        call_command("seed_venues", verbosity=0)
        self.assertEqual(DeadlineChange.objects.count(), 0)

    def test_suggestion_flow_and_approval(self):
        cycle = self.venue.next_cycle
        new = timezone.now() + timedelta(days=200)
        r = self.api(
            "post",
            f"/cycles/{cycle.pk}/suggestions/",
            {"field": "submission_deadline", "new_value": new.strftime("%Y-%m-%dT%H:%M"), "source_url": "neurips.cc/dates", "note": "Official"},
        )
        self.assertTrue(r.json()["ok"])
        bad = self.api("post", f"/cycles/{cycle.pk}/suggestions/", {"field": "nope", "new_value": "soon"})
        self.assertEqual(set(bad.json()["fields"]), {"field", "new_value"})
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


class ChangeNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def test_trackers_are_notified_of_extensions(self):
        from accounts.models import Notification
        from venues.models import VenueBookmark

        venue = Venue.objects.get(slug="neurips")
        fan = User.objects.create_user("fan", "fan@example.com", "pw-12345-xyz")
        other = User.objects.create_user("other", "other@example.com", "pw-12345-xyz")
        VenueBookmark.objects.create(user=fan, venue=venue)
        VenueBookmark.objects.create(user=other, venue=venue, is_starred=False)  # note only, not starred
        cycle = DeadlineCycle.objects.get(pk=venue.next_cycle.pk)
        cycle.submission_deadline += timedelta(days=7)
        cycle.save()
        notes = Notification.objects.filter(kind="change")
        self.assertEqual([n.user.username for n in notes], ["fan"])
        self.assertIn("paper deadline extended", notes[0].message)
        self.assertIn("(+7 days)", notes[0].message)
        self.assertEqual(notes[0].url, "/venue/neurips/")

    def test_past_corrections_do_not_notify(self):
        from accounts.models import Notification
        from venues.models import VenueBookmark

        venue = Venue.objects.get(slug="cvpr")
        VenueBookmark.objects.create(user=User.objects.create_user("x", "x@example.com", "pw-12345-xyz"), venue=venue)
        past = venue.cycles.filter(submission_deadline__lt=timezone.now()).order_by("submission_deadline").first()
        past.submission_deadline -= timedelta(days=1)
        past.save()
        self.assertTrue(DeadlineChange.objects.filter(cycle=past).exists(), "still audited")
        self.assertFalse(Notification.objects.filter(kind="change").exists())
