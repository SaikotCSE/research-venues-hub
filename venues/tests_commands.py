import json
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from community.models import DeadlineChange
from tracker.models import Submission

from .models import DeadlineCycle, Venue, VenueBookmark


def run(*args, **kwargs):
    out, err = StringIO(), StringIO()
    call_command(*args, stdout=out, stderr=err, **kwargs)
    return out.getvalue() + err.getvalue()


class ImportVenuesTests(TestCase):
    def write(self, text, suffix):
        fh = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
        fh.write(text)
        fh.close()
        self.addCleanup(Path(fh.name).unlink)
        return fh.name

    def test_json_round_trip_from_export(self):
        call_command("seed_venues", verbosity=0)
        exported = self.client.get(reverse("venues:export_json"), {"q": "miccai"}).content.decode()
        Venue.objects.filter(slug="miccai").delete()
        out = run("import_venues", self.write(exported, ".json"))
        self.assertIn("1 created", out)
        v = Venue.objects.get(slug="miccai")
        self.assertEqual(v.core_rank, "A")
        self.assertGreaterEqual(v.cycles.count(), 2)
        self.assertIn("Medical Image Analysis", v.subfields.values_list("name", flat=True))

    def test_csv_import_and_update(self):
        csv_text = (
            "acronym,name,venue_type,primary_domain,core_rank,impact_factor,subfields,is_open_access,official_website\n"
            "NEWCONF,New Conference,Conference,AI / Machine Learning,B,,Robotics; Planning,True,https://new.example.org\n"
        )
        out = run("import_venues", self.write(csv_text, ".csv"))
        self.assertIn("1 created", out)
        v = Venue.objects.get(slug="newconf")
        self.assertTrue(v.is_open_access)
        self.assertEqual(sorted(v.subfields.values_list("name", flat=True)), ["Planning", "Robotics"])
        out = run("import_venues", self.write(csv_text.replace(",B,", ",A,"), ".csv"))
        self.assertIn("1 updated", out)
        self.assertEqual(Venue.objects.get(slug="newconf").core_rank, "A")

    def test_dry_run_rolls_back(self):
        data = [{"acronym": "DRY", "name": "Dry Run Conf", "venue_type": "Conference", "primary_domain": "X",
                 "cycles": [{"year": 2031, "submission_deadline": "2031-03-01T11:59:00+00:00"}]}]
        out = run("import_venues", self.write(json.dumps(data), ".json"), "--dry-run")
        self.assertIn("[dry-run] 1 created", out)
        self.assertFalse(Venue.objects.filter(slug="dry").exists())

    def test_invalid_rows_are_reported(self):
        data = [
            {"acronym": "OK1", "name": "Fine", "venue_type": "Conference", "primary_domain": "X"},
            {"acronym": "BAD", "name": "Bad type", "venue_type": "Blog", "primary_domain": "X"},
            {"acronym": "BAD2", "name": "Bad cycle", "venue_type": "Journal", "primary_domain": "X", "cycles": [{"year": 2030}]},
            {"name": "", "acronym": ""},
        ]
        with self.assertRaises(CommandError):
            run("import_venues", self.write(json.dumps({"results": data}), ".json"))
        self.assertTrue(Venue.objects.filter(slug="ok1").exists())
        self.assertFalse(Venue.objects.filter(slug__in=["bad", "bad2"]).exists())

    def test_bad_input(self):
        with self.assertRaises(CommandError):
            run("import_venues", self.write("{not json", ".json"))
        with self.assertRaises(CommandError):
            run("import_venues", self.write("x", ".txt"))
        with self.assertRaises(CommandError):
            run("import_venues", "/no/such/file.csv")


class DigestAndDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def setUp(self):
        self.user = User.objects.create_user("alice", "alice@example.com", "pw-12345-xyz")
        venue = Venue.objects.create(name="Soon Conf", acronym="SOON", slug="soon", venue_type="Conference", primary_domain="X")
        DeadlineCycle.objects.create(venue=venue, year=2031, submission_deadline=timezone.now() + timedelta(days=9))
        VenueBookmark.objects.create(user=self.user, venue=venue)

    def test_digest_sends_html_and_text_once_per_week(self):
        out = run("send_digest", "--if-due")
        self.assertIn("1 digest(s) sent", out)
        msg = mail.outbox[0]
        self.assertIn("SOON 2031", msg.body)
        self.assertIn("text/html", msg.alternatives[0][1])
        self.assertIn("SOON 2031", msg.alternatives[0][0])
        run("send_digest", "--if-due")
        self.assertEqual(len(mail.outbox), 1, "not due again within 7 days")
        run("send_digest")
        self.assertEqual(len(mail.outbox), 2, "without --if-due it always sends")

    def test_digest_opt_out_and_nothing_to_report(self):
        p = self.user.profile
        p.weekly_digest = False
        p.save()
        User.objects.create_user("idle", "idle@example.com", "pw-12345-xyz")
        out = run("send_digest")
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("0 digest(s) sent", out)

    def test_seed_demo_is_idempotent(self):
        out = run("seed_demo", "--password", "demo-pass-123")
        self.assertIn("username='demo'", out)
        demo = User.objects.get(username="demo")
        first = (demo.submissions.count(), VenueBookmark.objects.filter(user=demo).count())
        run("seed_demo", "--password", "demo-pass-123")
        self.assertEqual(first, (demo.submissions.count(), VenueBookmark.objects.filter(user=demo).count()))
        self.assertTrue(self.client.login(username="demo", password="demo-pass-123"))
        self.assertContains(self.client.get(reverse("tracker:board")), "cardiac MRI")
        self.assertTrue(demo.venue_lists.filter(is_public=True).exists())
        submitted = Submission.objects.filter(user=demo, status__in=["submitted", "review"])
        self.assertTrue(all(s.cycle and s.cycle.submission_deadline < timezone.now() for s in submitted))


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)
        cls.admin = User.objects.create_superuser("admin", "admin@example.com", "pw-12345-xyz")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_changelists_render(self):
        for name in ("venues_venue", "venues_deadlinecycle", "venues_researchsubfield", "venues_venuebookmark",
                     "accounts_userprofile", "tracker_submission", "community_venuereview", "community_deadlinesuggestion"):
            r = self.client.get(reverse(f"admin:{name}_changelist"))
            self.assertEqual(r.status_code, 200, name)
        r = self.client.get(reverse("admin:venues_venue_changelist"), {"deadline": "30d"})
        self.assertEqual(r.status_code, 200)

    def test_venue_change_form_renders(self):
        v = Venue.objects.get(slug="cvpr")
        self.assertEqual(self.client.get(reverse("admin:venues_venue_change", args=[v.pk])).status_code, 200)

    def test_mark_verified_action(self):
        cycle = Venue.objects.get(slug="cvpr").next_cycle
        r = self.client.post(reverse("admin:venues_deadlinecycle_changelist"), {"action": "mark_verified", "_selected_action": [cycle.pk]}, follow=True)
        self.assertContains(r, "Marked 1 cycle(s) as verified")
        cycle.refresh_from_db()
        self.assertFalse(cycle.is_projected)
        self.assertIsNotNone(cycle.verified_at)
        self.assertContains(self.client.get(reverse("venues:detail", args=["cvpr"])), "Verified")
        self.assertEqual(DeadlineChange.objects.count(), 0, "verification is not a date change")

    def test_export_selected_csv_action(self):
        ids = list(Venue.objects.filter(slug__in=["cvpr", "icml"]).values_list("pk", flat=True))
        r = self.client.post(reverse("admin:venues_venue_changelist"), {"action": "export_selected_csv", "_selected_action": ids})
        self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(r.content.decode().count("\n"), 3)
