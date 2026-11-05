import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from venues.models import Venue

from .models import ChecklistItem, Paper, Submission

APP = "/api/app"


class TrackerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)
        cls.user = User.objects.create_user("alice", "a@example.com", "pw-12345-xyz")
        cls.other = User.objects.create_user("bob", "b@example.com", "pw-12345-xyz")
        cls.venue = Venue.objects.get(slug="cvpr")

    def setUp(self):
        self.client.force_login(self.user)

    def api(self, method, path, body=None):
        return getattr(self.client, method)(APP + path, data=json.dumps(body or {}), content_type="application/json")

    def make_sub(self, **kw):
        paper = kw.pop("paper", None) or Paper.objects.create(user=self.user, title="My Paper")
        return Submission.objects.create(user=self.user, paper=paper, venue=self.venue, cycle=self.venue.next_cycle, **kw)

    def test_create_with_new_paper_and_checklist(self):
        r = self.api(
            "post", "/tracker/submissions/", {"new_paper_title": "Great Idea", "venue": "cvpr", "cycle": self.venue.next_cycle.pk, "status": "writing"}
        )
        self.assertEqual(r.status_code, 200)
        sub = Submission.objects.get(paper__title="Great Idea")
        detail = r.json()["submission"]
        self.assertEqual((detail["id"], detail["status"], detail["venue"]["acronym"]), (sub.pk, "writing", "CVPR"))
        items = [i["text"] for i in detail["checklist_items"]]
        self.assertTrue(any("CVPR" in t for t in items))
        self.assertTrue(any("Anonymise" in t for t in items), "double-blind venue gets anonymity task")

    def test_new_page_requires_login(self):
        self.assertEqual(self.client.get(reverse("tracker:create") + "?venue=cvpr").status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("tracker:create")).status_code, 302)

    def test_create_requires_paper_and_venue(self):
        r = self.api("post", "/tracker/submissions/", {"venue": "cvpr", "status": "planning"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Choose an existing paper", r.json()["error"])
        r = self.api("post", "/tracker/submissions/", {"new_paper_title": "X", "venue": "no-such-venue", "status": "planning"})
        self.assertIn("venue", r.json()["fields"])

    def test_cycle_must_match_venue(self):
        other_cycle = Venue.objects.get(slug="icml").next_cycle
        r = self.api("post", "/tracker/submissions/", {"new_paper_title": "X", "venue": "cvpr", "cycle": other_cycle.pk, "status": "planning"})
        self.assertIn("different venue", r.json()["fields"]["cycle"][0])

    def test_board_columns_and_stats(self):
        self.make_sub(status="writing")
        self.make_sub(status="accepted")
        self.make_sub(status="rejected")
        data = self.client.get(f"{APP}/tracker/board/").json()
        self.assertEqual(data["stats"], {"total": 3, "active": 1, "accepted": 1, "rate": 50})
        self.assertEqual([len(c["items"]) for c in data["columns"]][:2], [0, 1])
        self.assertEqual(data["columns"][0]["key"], "planning")

    def test_status_change_sets_dates(self):
        sub = self.make_sub()
        self.api("patch", f"/tracker/submissions/{sub.pk}/", {"status": "submitted"})
        sub.refresh_from_db()
        self.assertEqual((sub.status, sub.submitted_on), ("submitted", timezone.localdate()))
        self.api("patch", f"/tracker/submissions/{sub.pk}/", {"status": "accepted"})
        sub.refresh_from_db()
        self.assertEqual(sub.decision_on, timezone.localdate())
        self.assertEqual(self.api("patch", f"/tracker/submissions/{sub.pk}/", {"status": "nonsense"}).status_code, 400)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "accepted")

    def test_checklist_toggle_add_and_delete(self):
        sub = self.make_sub()
        detail = self.client.get(f"{APP}/tracker/submissions/{sub.pk}/").json()  # seeds the checklist
        item = detail["checklist_items"][0]
        self.assertTrue(self.api("patch", f"/tracker/submissions/{sub.pk}/checklist/{item['id']}/", {"done": True}).json()["item"]["done"])
        added = self.api("post", f"/tracker/submissions/{sub.pk}/checklist/", {"text": "Write rebuttal plan"}).json()["item"]
        self.assertTrue(sub.checklist_items.filter(text="Write rebuttal plan").exists())
        self.assertEqual(self.api("post", f"/tracker/submissions/{sub.pk}/checklist/", {"text": "  "}).status_code, 400)
        done, total = sub.checklist_progress
        self.assertEqual((done, total), (1, sub.checklist_items.count()))
        self.api("delete", f"/tracker/submissions/{sub.pk}/checklist/{added['id']}/")
        self.assertFalse(sub.checklist_items.filter(text="Write rebuttal plan").exists())

    def test_isolation_between_users(self):
        sub = self.make_sub()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("tracker:detail", args=[sub.pk])).status_code, 404)
        self.assertEqual(self.client.get(f"{APP}/tracker/submissions/{sub.pk}/").status_code, 404)
        self.assertEqual(self.api("patch", f"/tracker/submissions/{sub.pk}/", {"status": "review"}).status_code, 404)
        self.assertEqual(self.api("delete", f"/tracker/submissions/{sub.pk}/").status_code, 404)
        item = ChecklistItem.objects.create(submission=sub, text="t")
        self.assertEqual(self.api("patch", f"/tracker/submissions/{sub.pk}/checklist/{item.pk}/", {"done": True}).status_code, 404)
        foreign_paper = Paper.objects.create(user=self.user, title="Alice's")
        r = self.api("post", "/tracker/submissions/", {"paper": foreign_paper.pk, "venue": "cvpr", "status": "planning"})
        self.assertIn("paper", r.json()["fields"])

    def test_edit_and_delete(self):
        sub = self.make_sub()
        r = self.api("patch", f"/tracker/submissions/{sub.pk}/", {"cycle": sub.cycle.pk, "status": "review", "notes": "waiting"})
        self.assertEqual(r.json()["notes"], "waiting")
        sub.refresh_from_db()
        self.assertEqual((sub.status, sub.notes, sub.paper.title), ("review", "waiting", "My Paper"))
        self.api("delete", f"/tracker/submissions/{sub.pk}/")
        self.assertFalse(Submission.objects.filter(pk=sub.pk).exists())

    def test_papers_crud(self):
        r = self.api("post", "/tracker/papers/", {"title": "P1", "keywords": "vision"})
        p = Paper.objects.get(title="P1")
        self.assertEqual(r.json()["paper"]["id"], p.pk)
        self.assertEqual([x["title"] for x in self.client.get(f"{APP}/tracker/papers/").json()["results"]], ["P1"])
        self.assertEqual(self.api("patch", f"/tracker/papers/{p.pk}/", {"title": "P1 (v2)"}).json()["paper"]["title"], "P1 (v2)")
        self.assertEqual(self.api("post", "/tracker/papers/", {"title": ""}).status_code, 400)
        self.api("delete", f"/tracker/papers/{p.pk}/")
        self.assertFalse(Paper.objects.exists())

    def test_days_to_deadline(self):
        sub = self.make_sub()
        sub.cycle.submission_deadline = timezone.now() + timedelta(days=10, hours=1)
        sub.cycle.save()
        self.assertEqual(sub.days_to_deadline, 10)

    def test_api_submissions(self):
        self.make_sub(status="writing")
        t = self.user.profile.issue_api_token()
        data = self.client.get(reverse("venues:api_me_submissions"), HTTP_AUTHORIZATION=f"Bearer {t}").json()
        self.assertEqual(data["results"][0]["venue"], "CVPR")
