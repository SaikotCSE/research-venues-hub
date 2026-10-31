from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from venues.models import Venue

from .models import ChecklistItem, Paper, Submission


class TrackerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)
        cls.user = User.objects.create_user("alice", "a@example.com", "pw-12345-xyz")
        cls.other = User.objects.create_user("bob", "b@example.com", "pw-12345-xyz")
        cls.venue = Venue.objects.get(slug="cvpr")

    def setUp(self):
        self.client.force_login(self.user)

    def make_sub(self, **kw):
        paper = kw.pop("paper", None) or Paper.objects.create(user=self.user, title="My Paper")
        return Submission.objects.create(user=self.user, paper=paper, venue=self.venue, cycle=self.venue.next_cycle, **kw)

    def test_create_with_new_paper_and_checklist(self):
        r = self.client.post(
            reverse("tracker:create") + "?venue=cvpr",
            {"new_paper_title": "Great Idea", "venue": self.venue.pk, "cycle": self.venue.next_cycle.pk, "status": "writing"},
        )
        sub = Submission.objects.get(paper__title="Great Idea")
        self.assertRedirects(r, reverse("tracker:detail", args=[sub.pk]))
        items = list(sub.checklist_items.values_list("text", flat=True))
        self.assertTrue(any("CVPR" in t for t in items))
        self.assertTrue(any("Anonymise" in t for t in items), "double-blind venue gets anonymity task")

    def test_create_prefills_from_query(self):
        r = self.client.get(reverse("tracker:create") + "?venue=cvpr")
        self.assertContains(r, f'value="{self.venue.pk}" selected')

    def test_create_requires_paper(self):
        r = self.client.post(reverse("tracker:create"), {"venue": self.venue.pk, "status": "planning"})
        self.assertContains(r, "Choose an existing paper")

    def test_cycle_must_match_venue(self):
        other_cycle = Venue.objects.get(slug="icml").next_cycle
        r = self.client.post(reverse("tracker:create"), {"new_paper_title": "X", "venue": self.venue.pk, "cycle": other_cycle.pk, "status": "planning"})
        self.assertContains(r, "different venue")

    def test_board_columns_and_stats(self):
        self.make_sub(status="writing")
        self.make_sub(status="accepted")
        self.make_sub(status="rejected")
        r = self.client.get(reverse("tracker:board"))
        self.assertEqual(r.context["stats"], {"total": 3, "active": 1, "accepted": 1, "rate": 50})
        self.assertEqual([len(c["items"]) for c in r.context["columns"]][:2], [0, 1])

    def test_status_change_sets_dates(self):
        sub = self.make_sub()
        self.client.post(reverse("tracker:status", args=[sub.pk]), {"status": "submitted"})
        sub.refresh_from_db()
        self.assertEqual((sub.status, sub.submitted_on), ("submitted", timezone.localdate()))
        self.client.post(reverse("tracker:status", args=[sub.pk]), {"status": "accepted"})
        sub.refresh_from_db()
        self.assertEqual(sub.decision_on, timezone.localdate())
        self.client.post(reverse("tracker:status", args=[sub.pk]), {"status": "nonsense"})
        sub.refresh_from_db()
        self.assertEqual(sub.status, "accepted")

    def test_htmx_status_returns_refresh(self):
        sub = self.make_sub()
        r = self.client.post(reverse("tracker:status", args=[sub.pk]), {"status": "review"}, HTTP_HX_REQUEST="true")
        self.assertEqual((r.status_code, r["HX-Refresh"]), (204, "true"))

    def test_checklist_toggle_and_add(self):
        sub = self.make_sub()
        self.client.get(reverse("tracker:detail", args=[sub.pk]))
        item = sub.checklist_items.first()
        r = self.client.post(reverse("tracker:checklist_toggle", args=[sub.pk, item.pk]))
        self.assertContains(r, "line-through")
        self.client.post(reverse("tracker:checklist_add", args=[sub.pk]), {"text": "Write rebuttal plan"})
        self.assertTrue(sub.checklist_items.filter(text="Write rebuttal plan").exists())
        done, total = sub.checklist_progress
        self.assertEqual((done, total), (1, sub.checklist_items.count()))

    def test_isolation_between_users(self):
        sub = self.make_sub()
        self.client.force_login(self.other)
        for name, args in (("tracker:detail", [sub.pk]),):
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 404)
        self.assertEqual(self.client.post(reverse("tracker:status", args=[sub.pk]), {"status": "review"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("tracker:delete", args=[sub.pk])).status_code, 404)
        item = ChecklistItem.objects.create(submission=sub, text="t")
        self.assertEqual(self.client.post(reverse("tracker:checklist_toggle", args=[sub.pk, item.pk])).status_code, 404)

    def test_edit_and_delete(self):
        sub = self.make_sub()
        r = self.client.post(
            reverse("tracker:detail", args=[sub.pk]),
            {"paper": sub.paper.pk, "venue": self.venue.pk, "cycle": sub.cycle.pk, "status": "review", "notes": "waiting"},
        )
        self.assertRedirects(r, reverse("tracker:detail", args=[sub.pk]))
        sub.refresh_from_db()
        self.assertEqual((sub.status, sub.notes), ("review", "waiting"))
        self.client.post(reverse("tracker:delete", args=[sub.pk]))
        self.assertFalse(Submission.objects.filter(pk=sub.pk).exists())

    def test_papers_crud(self):
        self.client.post(reverse("tracker:papers"), {"title": "P1", "keywords": "vision"})
        p = Paper.objects.get(title="P1")
        self.assertContains(self.client.get(reverse("tracker:papers")), "P1")
        self.client.post(reverse("tracker:paper_delete", args=[p.pk]))
        self.assertFalse(Paper.objects.exists())

    def test_days_to_deadline(self):
        sub = self.make_sub()
        sub.cycle.submission_deadline = timezone.now() + timedelta(days=10, hours=1)
        sub.cycle.save()
        self.assertEqual(sub.days_to_deadline, 10)

    def test_api_submissions(self):
        self.make_sub(status="writing")
        t = self.user.profile.api_token
        data = self.client.get(reverse("venues:api_me_submissions"), HTTP_AUTHORIZATION=f"Bearer {t}").json()
        self.assertEqual(data["results"][0]["venue"], "CVPR")


class TrackerDragDropTests(TestCase):
    def test_json_status_change_keeps_flash_message_for_reload(self):
        call_command("seed_venues", verbosity=0)
        user = User.objects.create_user("dd", "dd@example.com", "pw-12345-xyz")
        venue = Venue.objects.get(slug="cvpr")
        sub = Submission.objects.create(user=user, paper=Paper.objects.create(user=user, title="P"), venue=venue)
        self.client.force_login(user)
        r = self.client.post(reverse("tracker:status", args=[sub.pk]), {"status": "writing"}, HTTP_ACCEPT="application/json")
        self.assertEqual(r.json(), {"status": "writing"})
        self.assertContains(self.client.get(reverse("tracker:board")), "Moved “P” to Writing")
