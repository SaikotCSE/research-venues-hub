from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Notification, SavedSearch, VenueList
from venues.models import DeadlineCycle, Venue, VenueBookmark


class AccountTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)
        cls.user = User.objects.create_user("alice", "alice@example.com", "pw-12345-xyz")

    def login(self):
        self.client.force_login(self.user)


class AuthTests(AccountTestBase):
    def test_profile_autocreated(self):
        self.assertTrue(self.user.profile.calendar_token)
        self.assertNotEqual(self.user.profile.calendar_token, self.user.profile.api_token)

    def test_signup_flow(self):
        r = self.client.post(reverse("accounts:signup"), {"username": "bob", "email": "bob@example.com",
                                                          "password1": "S3cure-pass-987", "password2": "S3cure-pass-987"})
        self.assertRedirects(r, reverse("accounts:profile"))
        self.assertTrue(User.objects.get(username="bob").profile)

    def test_signup_rejects_duplicate_email(self):
        r = self.client.post(reverse("accounts:signup"), {"username": "bob", "email": "ALICE@example.com",
                                                          "password1": "S3cure-pass-987", "password2": "S3cure-pass-987"})
        self.assertContains(r, "already exists")

    def test_login_logout(self):
        r = self.client.post(reverse("accounts:login"), {"username": "alice", "password": "pw-12345-xyz"})
        self.assertRedirects(r, reverse("accounts:dashboard"))
        self.client.post(reverse("accounts:logout"))
        self.assertEqual(self.client.get(reverse("accounts:dashboard")).status_code, 302)

    def test_login_required_pages(self):
        for name in ("accounts:dashboard", "accounts:profile", "accounts:notifications", "accounts:lists", "tracker:board", "tracker:create"):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn("/accounts/login/", r["Location"])

    def test_anonymous_bookmarks_merge_on_login(self):
        c = Client()
        c.post(reverse("venues:bookmark", args=["cvpr"]))
        c.post(reverse("venues:note", args=["kdd"]), {"note": "hello"})
        self.assertEqual(VenueBookmark.objects.filter(user__isnull=True).count(), 2)
        c.post(reverse("accounts:login"), {"username": "alice", "password": "pw-12345-xyz"})
        self.assertEqual(VenueBookmark.objects.filter(user=self.user).count(), 2)
        self.assertEqual(VenueBookmark.objects.filter(user__isnull=True).count(), 0)
        self.assertContains(c.get(reverse("venues:targets")), "CVPR")

    def test_bookmarks_follow_user_across_clients(self):
        self.login()
        self.client.post(reverse("venues:bookmark", args=["icml"]))
        other = Client()
        other.force_login(self.user)
        self.assertContains(other.get(reverse("venues:targets")), "ICML")

    def test_dashboard_and_profile(self):
        self.login()
        self.client.post(reverse("venues:bookmark", args=["cvpr"]))
        self.assertContains(self.client.get(reverse("accounts:dashboard")), "Welcome back")
        r = self.client.post(reverse("accounts:profile"), {"display_name": "Alice", "affiliation": "MIT", "research_interests": "vision, medical imaging",
                                                           "timezone": "Europe/Paris", "email_reminders": "on", "reminder_days": "30, 3"})
        self.assertRedirects(r, reverse("accounts:profile"))
        p = User.objects.get(pk=self.user.pk).profile
        self.assertEqual((p.timezone, p.reminder_offsets, p.interest_keywords), ("Europe/Paris", [30, 3], ["vision", "medical imaging"]))
        self.assertContains(self.client.get(reverse("accounts:dashboard")), "Recommended for your interests")

    def test_profile_rejects_bad_reminders(self):
        self.login()
        r = self.client.post(reverse("accounts:profile"), {"timezone": "UTC", "reminder_days": "soon"})
        self.assertContains(r, "comma-separated day counts")

    def test_token_regeneration(self):
        self.login()
        old = self.user.profile.api_token
        self.client.post(reverse("accounts:regenerate_token", args=["api"]))
        self.assertNotEqual(User.objects.get(pk=self.user.pk).profile.api_token, old)
        self.assertEqual(self.client.post(reverse("accounts:regenerate_token", args=["bogus"])).status_code, 404)


class ListsAndSearchTests(AccountTestBase):
    def test_list_lifecycle_and_privacy(self):
        self.login()
        r = self.client.post(reverse("accounts:list_create"), {"name": "ML 2027", "description": "targets"})
        lst = VenueList.objects.get(name="ML 2027")
        self.assertRedirects(r, reverse("accounts:list_detail", args=[lst.slug]))
        self.client.post(reverse("accounts:list_toggle", args=[lst.slug, "neurips"]))
        self.assertEqual(list(lst.venues.values_list("acronym", flat=True)), ["NeurIPS"])
        self.assertContains(self.client.get(reverse("venues:detail", args=["icml"])), "ML 2027")
        # private -> hidden from others, public -> visible
        anon = Client()
        self.assertEqual(anon.get(reverse("accounts:list_detail", args=[lst.slug])).status_code, 404)
        self.client.post(reverse("accounts:list_update", args=[lst.slug]), {"is_public": "on"})
        self.assertContains(anon.get(reverse("accounts:list_detail", args=[lst.slug])), "NeurIPS")
        self.client.post(reverse("accounts:list_toggle", args=[lst.slug, "neurips"]))
        self.assertEqual(lst.venues.count(), 0)

    def test_cannot_edit_others_lists(self):
        other = User.objects.create_user("eve", "eve@example.com", "pw-12345-xyz")
        lst = VenueList.objects.create(user=other, name="Eve", is_public=True)
        self.login()
        self.assertEqual(self.client.post(reverse("accounts:list_toggle", args=[lst.slug, "cvpr"])).status_code, 404)
        self.assertEqual(self.client.post(reverse("accounts:list_update", args=[lst.slug]), {"action": "delete"}).status_code, 404)
        self.assertTrue(VenueList.objects.filter(pk=lst.pk).exists())

    def test_list_toggle_open_redirect_blocked(self):
        self.login()
        lst = VenueList.objects.create(user=self.user, name="X")
        r = self.client.post(reverse("accounts:list_toggle", args=[lst.slug, "cvpr"]), {"next": "//evil.example.com"})
        self.assertEqual(r["Location"], reverse("accounts:list_detail", args=[lst.slug]))

    def test_saved_search(self):
        self.login()
        r = self.client.post(reverse("accounts:search_save"), {"name": "Open A*", "querystring": "status=open&core=A*", "alert": "on"})
        s = SavedSearch.objects.get(name="Open A*")
        self.assertTrue(s.alert and s.last_count > 0)
        self.assertIn("status=open", r["Location"])
        self.assertContains(self.client.get(reverse("accounts:dashboard")), "Open A*")
        self.client.post(reverse("accounts:search_delete", args=[s.pk]))
        self.assertFalse(SavedSearch.objects.exists())

    def test_calendar_feed(self):
        self.login()
        self.client.post(reverse("venues:bookmark", args=["cvpr"]))
        token = self.user.profile.calendar_token
        r = Client().get(reverse("accounts:calendar_feed", args=[token]))
        self.assertEqual(r.status_code, 200)
        self.assertIn("SUMMARY:CVPR", r.content.decode())
        self.assertEqual(Client().get(reverse("accounts:calendar_feed", args=["wrong"])).status_code, 404)


class ReminderTests(AccountTestBase):
    def setUp(self):
        v = Venue.objects.create(name="Soon Conf", acronym="SOON", slug="soon", venue_type="Conference", primary_domain="X")
        self.cycle = DeadlineCycle.objects.create(venue=v, year=2031, submission_deadline=timezone.now() + timedelta(days=5),
                                                  submission_open_date=timezone.now() - timedelta(days=30))
        VenueBookmark.objects.create(user=self.user, venue=v)

    def run_cmd(self, *args):
        out = StringIO()
        call_command("send_reminders", *args, stdout=out)
        return out.getvalue()

    def test_creates_notification_and_email_once(self):
        self.run_cmd()
        self.assertEqual(Notification.objects.filter(user=self.user, kind="deadline").count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("SOON", mail.outbox[0].subject)
        self.run_cmd()
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1, "idempotent")
        self.assertEqual(len(mail.outbox), 1)

    def test_dry_run_and_opt_out(self):
        self.assertIn("dry-run", self.run_cmd("--dry-run"))
        self.assertEqual(Notification.objects.count(), 0)
        p = self.user.profile
        p.email_reminders = False
        p.save()
        self.run_cmd()
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_far_deadlines_ignored(self):
        self.cycle.submission_deadline = timezone.now() + timedelta(days=100)
        self.cycle.save()
        self.run_cmd()
        self.assertEqual(Notification.objects.count(), 0)

    def test_saved_search_alert(self):
        s = SavedSearch.objects.create(user=self.user, name="Everything", querystring="", alert=True, last_count=0)
        self.run_cmd()
        self.assertTrue(Notification.objects.filter(kind="search").exists())
        s.refresh_from_db()
        self.assertEqual(s.last_count, Venue.objects.count())

    def test_notifications_page_and_mark_read(self):
        self.run_cmd()
        self.login()
        self.assertContains(self.client.get(reverse("accounts:notifications")), "SOON")
        self.assertContains(self.client.get(reverse("accounts:dashboard")), "Unread notifications")
        self.client.post(reverse("accounts:notifications_read"))
        self.assertEqual(self.user.notifications.filter(read_at__isnull=True).count(), 0)
