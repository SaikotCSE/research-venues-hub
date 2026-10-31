import json
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

APP = "/api/app"


def boot_of(response):
    """The JSON the shell embeds for the React app."""
    return json.loads(response.content.decode().split('id="vp-boot" type="application/json">')[1].split("</script>")[0])


class AccountTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)
        cls.user = User.objects.create_user("alice", "alice@example.com", "pw-12345-xyz")

    def login(self):
        self.client.force_login(self.user)

    def api(self, method, path, body=None, client=None):
        client = client or self.client
        return getattr(client, method)(APP + path, data=json.dumps(body or {}), content_type="application/json")


class AuthTests(AccountTestBase):
    def test_profile_autocreated(self):
        self.assertTrue(self.user.profile.calendar_token)
        self.assertNotEqual(self.user.profile.calendar_token, self.user.profile.api_token)

    def signup(self, **overrides):
        data = {"username": "bob", "email": "bob@example.com", "password1": "S3cure-pass-987", "password2": "S3cure-pass-987", **overrides}
        return self.api("post", "/auth/signup/", data)

    def test_signup_flow(self):
        r = self.signup()
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["authenticated"])
        self.assertEqual((data["user"]["username"], data["next"]), ("bob", reverse("accounts:profile")))
        self.assertTrue(User.objects.get(username="bob").profile)

    def test_signup_validation_errors_are_per_field(self):
        r = self.signup(email="ALICE@example.com", password2="mismatch")
        self.assertEqual(r.status_code, 400)
        fields = r.json()["fields"]
        self.assertIn("already exists", fields["email"][0])
        self.assertIn("password2", fields)
        self.assertEqual(self.api("post", "/auth/signup/", {}).json()["error"], "Please correct the highlighted fields.")

    def test_login_logout(self):
        r = self.api("post", "/auth/login/", {"username": "alice", "password": "pw-12345-xyz"})
        self.assertEqual(r.json()["next"], reverse("accounts:dashboard"))
        self.assertEqual(self.client.get(f"{APP}/me/dashboard/").status_code, 200)
        out = self.api("post", "/auth/logout/").json()
        self.assertFalse(out["authenticated"])
        self.assertEqual(self.client.get(f"{APP}/me/dashboard/").status_code, 401)

    def test_bad_login(self):
        r = self.api("post", "/auth/login/", {"username": "alice", "password": "nope"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("correct username and password", r.json()["error"])

    def test_login_required_pages_and_endpoints(self):
        for name in ("accounts:dashboard", "accounts:profile", "accounts:notifications", "accounts:lists", "tracker:board", "tracker:create"):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn("/accounts/login/", r["Location"])
        for path in ("/me/dashboard/", "/me/profile/", "/me/notifications/", "/lists/", "/tracker/board/"):
            self.assertEqual(self.client.get(APP + path).status_code, 401, path)

    def test_signed_in_users_skip_login_page(self):
        self.login()
        self.assertRedirects(self.client.get(reverse("accounts:login")), reverse("accounts:dashboard"), fetch_redirect_response=False)

    def test_anonymous_bookmarks_merge_on_login(self):
        c = Client()
        self.api("post", "/venues/cvpr/star/", client=c)
        self.api("put", "/venues/kdd/note/", {"note": "hello"}, client=c)
        self.assertEqual(VenueBookmark.objects.filter(user__isnull=True).count(), 2)
        self.api("post", "/auth/login/", {"username": "alice", "password": "pw-12345-xyz"}, client=c)
        self.assertEqual(VenueBookmark.objects.filter(user=self.user).count(), 2)
        self.assertEqual(VenueBookmark.objects.filter(user__isnull=True).count(), 0)
        self.assertEqual([v["acronym"] for v in c.get(f"{APP}/targets/").json()["results"]], ["CVPR"])

    def test_bookmarks_follow_user_across_clients(self):
        self.login()
        self.api("post", "/venues/icml/star/")
        other = Client()
        other.force_login(self.user)
        self.assertEqual([v["acronym"] for v in other.get(f"{APP}/targets/").json()["results"]], ["ICML"])

    def test_session_payload(self):
        anon = self.client.get(f"{APP}/session/").json()
        self.assertEqual((anon["authenticated"], anon["user"]), (False, None))
        self.assertTrue(anon["csrf_token"])
        self.login()
        me = self.client.get(f"{APP}/session/").json()
        self.assertEqual(me["user"]["username"], "alice")
        self.assertEqual(me["user"]["initials"], "AL")
        self.assertIsNone(me["admin_url"])

    def test_dashboard_and_profile(self):
        self.login()
        self.api("post", "/venues/cvpr/star/")
        dash = self.client.get(f"{APP}/me/dashboard/").json()
        self.assertEqual(dash["target_count"], 1)
        self.assertEqual(dash["recommendations"], [])
        self.assertFalse(dash["onboarding"][0]["done"])
        r = self.api(
            "put",
            "/me/profile/",
            {
                "display_name": "Alice",
                "affiliation": "MIT",
                "research_interests": "vision, medical imaging",
                "timezone": "Europe/Paris",
                "email_reminders": True,
                "reminder_days": "30, 3",
            },
        )
        self.assertEqual(r.status_code, 200)
        p = User.objects.get(pk=self.user.pk).profile
        self.assertEqual((p.timezone, p.reminder_offsets, p.interest_keywords), ("Europe/Paris", [30, 3], ["vision", "medical imaging"]))
        self.assertTrue(self.client.get(f"{APP}/me/dashboard/").json()["recommendations"])

    def test_profile_partial_update_keeps_other_fields(self):
        self.login()
        self.api("put", "/me/profile/", {"affiliation": "ETH"})
        p = User.objects.get(pk=self.user.pk).profile
        self.assertEqual((p.affiliation, p.reminder_days, p.timezone), ("ETH", "14,7,1", "UTC"))

    def test_profile_rejects_bad_reminders(self):
        self.login()
        r = self.api("put", "/me/profile/", {"reminder_days": "soon"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("comma-separated day counts", r.json()["fields"]["reminder_days"][0])

    def test_token_regeneration(self):
        self.login()
        old = self.user.profile.api_token
        r = self.api("post", "/me/tokens/api/")
        self.assertNotEqual(r.json()["api_token"], old)
        self.assertNotEqual(User.objects.get(pk=self.user.pk).profile.api_token, old)
        self.assertEqual(self.api("post", "/me/tokens/bogus/").status_code, 404)


class ListsAndSearchTests(AccountTestBase):
    def test_list_lifecycle_and_privacy(self):
        self.login()
        r = self.api("post", "/lists/", {"name": "ML 2027", "description": "targets"})
        lst = VenueList.objects.get(name="ML 2027")
        self.assertEqual(r.json()["list"]["slug"], lst.slug)
        self.assertTrue(self.api("post", f"/lists/{lst.slug}/venues/neurips/").json()["member"])
        self.assertEqual(list(lst.venues.values_list("acronym", flat=True)), ["NeurIPS"])
        me = self.client.get(f"{APP}/venues/icml/").json()["me"]
        self.assertEqual(me["lists"], [{"slug": lst.slug, "name": "ML 2027", "member": False}])
        # private -> hidden from others, public -> visible
        anon = Client()
        self.assertEqual(anon.get(reverse("accounts:list_detail", args=[lst.slug])).status_code, 404)
        self.assertEqual(anon.get(f"{APP}/lists/{lst.slug}/").status_code, 404)
        self.assertTrue(self.api("patch", f"/lists/{lst.slug}/", {"is_public": True}).json()["list"]["is_public"])
        shell = anon.get(reverse("accounts:list_detail", args=[lst.slug]))
        self.assertEqual(boot_of(shell)["initial"]["list"]["venues"][0]["acronym"], "NeurIPS")
        self.assertFalse(self.api("post", f"/lists/{lst.slug}/venues/neurips/").json()["member"])
        self.assertEqual(lst.venues.count(), 0)
        self.assertEqual(self.api("delete", f"/lists/{lst.slug}/").status_code, 200)
        self.assertFalse(VenueList.objects.filter(pk=lst.pk).exists())

    def test_cannot_edit_others_lists(self):
        other = User.objects.create_user("eve", "eve@example.com", "pw-12345-xyz")
        lst = VenueList.objects.create(user=other, name="Eve", is_public=True)
        self.login()
        self.assertEqual(self.api("post", f"/lists/{lst.slug}/venues/cvpr/").status_code, 404)
        self.assertEqual(self.api("delete", f"/lists/{lst.slug}/").status_code, 403)
        self.assertEqual(self.api("patch", f"/lists/{lst.slug}/", {"is_public": False}).status_code, 403)
        self.assertTrue(VenueList.objects.get(pk=lst.pk).is_public)

    def test_saved_search(self):
        self.login()
        r = self.api("post", "/me/searches/", {"name": "Open A*", "querystring": "?status=open&core=A*", "alert": True})
        s = SavedSearch.objects.get(name="Open A*")
        self.assertTrue(s.alert and s.last_count > 0)
        self.assertEqual(s.querystring, "status=open&core=A*")
        self.assertEqual(r.json()["search"]["id"], s.pk)
        self.assertEqual([x["name"] for x in self.client.get(f"{APP}/me/dashboard/").json()["saved_searches"]], ["Open A*"])
        self.assertEqual(self.api("post", "/me/searches/", {"querystring": "q=x"}).status_code, 400)
        self.api("delete", f"/me/searches/{s.pk}/")
        self.assertFalse(SavedSearch.objects.exists())

    def test_calendar_feed(self):
        self.login()
        self.api("post", "/venues/cvpr/star/")
        token = self.user.profile.calendar_token
        r = Client().get(reverse("accounts:calendar_feed", args=[token]))
        self.assertEqual(r.status_code, 200)
        self.assertIn("SUMMARY:CVPR", r.content.decode())
        self.assertEqual(Client().get(reverse("accounts:calendar_feed", args=["wrong"])).status_code, 404)


class ReminderTests(AccountTestBase):
    def setUp(self):
        profile = self.user.profile
        profile.verified_email = self.user.email
        profile.save()
        v = Venue.objects.create(name="Soon Conf", acronym="SOON", slug="soon", venue_type="Conference", primary_domain="X")
        self.cycle = DeadlineCycle.objects.create(
            venue=v, year=2031, submission_deadline=timezone.now() + timedelta(days=5), submission_open_date=timezone.now() - timedelta(days=30)
        )
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
        self.cycle.save()  # moving a tracked deadline creates a "change" notification...
        self.run_cmd()
        self.assertEqual(Notification.objects.filter(kind="deadline").count(), 0)  # ...but no reminder is due
        self.assertEqual(Notification.objects.filter(kind="change").count(), 1)

    def test_saved_search_alert(self):
        s = SavedSearch.objects.create(user=self.user, name="Everything", querystring="", alert=True, last_count=0)
        self.run_cmd()
        self.assertTrue(Notification.objects.filter(kind="search").exists())
        s.refresh_from_db()
        self.assertEqual(s.last_count, Venue.objects.count())

    def test_notifications_api_and_mark_read(self):
        self.run_cmd()
        self.login()
        data = self.client.get(f"{APP}/me/notifications/").json()
        self.assertIn("SOON", data["results"][0]["message"])
        self.assertEqual(data["unread_count"], 1)
        self.assertEqual(self.client.get(f"{APP}/me/dashboard/").json()["unread_count"], 1)
        self.assertEqual(self.api("post", "/me/notifications/read/").json(), {"marked": 1, "unread_count": 0})
        self.assertEqual(self.user.notifications.filter(read_at__isnull=True).count(), 0)


class AccountManagementTests(AccountTestBase):
    def test_password_reset_end_to_end(self):
        r = self.api("post", "/auth/password-reset/", {"email": "ALICE@example.com"})
        self.assertEqual(r.json(), {"ok": True})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Reset", mail.outbox[0].subject)
        link = next(line for line in mail.outbox[0].body.splitlines() if "/accounts/password/reset/" in line).strip()
        path = link.split("testserver", 1)[1]
        uid = path.rstrip("/").split("/")[-2]
        r = self.client.get(path)  # the token moves into the session, out of the address bar
        self.assertRedirects(r, reverse("accounts:password_reset_confirm", args=[uid, "set-password"]), fetch_redirect_response=False)
        page = self.client.get(r["Location"])
        self.assertEqual(boot_of(page)["extra"]["reset"], {"valid": True, "uid": uid})
        bad = self.api("post", "/auth/password-reset/confirm/", {"uid": uid, "new_password1": "short", "new_password2": "short"})
        self.assertEqual(bad.status_code, 400)
        ok = self.api("post", "/auth/password-reset/confirm/", {"uid": uid, "new_password1": "Brand-new-pass-77", "new_password2": "Brand-new-pass-77"})
        self.assertEqual(ok.json(), {"ok": True})
        self.assertTrue(self.client.login(username="alice", password="Brand-new-pass-77"))
        # the link works once
        again = self.api("post", "/auth/password-reset/confirm/", {"uid": uid, "new_password1": "Other-pass-777", "new_password2": "Other-pass-777"})
        self.assertEqual(again.status_code, 400)

    def test_password_reset_unknown_email_is_silent(self):
        self.assertEqual(self.api("post", "/auth/password-reset/", {"email": "nobody@example.com"}).json(), {"ok": True})
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_reset_link(self):
        r = self.client.get(reverse("accounts:password_reset_confirm", args=["MQ", "bad-token"]))
        self.assertEqual(boot_of(r)["extra"]["reset"], {"valid": False, "uid": "MQ"})

    def test_password_change(self):
        self.login()
        r = self.api("post", "/auth/password-change/", {"old_password": "pw-12345-xyz", "new_password1": "Another-pass-55", "new_password2": "Another-pass-55"})
        self.assertTrue(r.json()["ok"])
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password("Another-pass-55"))
        self.assertEqual(self.client.get(f"{APP}/me/dashboard/").status_code, 200, "session survives password change")
        wrong = self.api("post", "/auth/password-change/", {"old_password": "nope", "new_password1": "x", "new_password2": "x"})
        self.assertIn("old_password", wrong.json()["fields"])

    def test_email_change_and_uniqueness(self):
        User.objects.create_user("bob", "bob@example.com", "pw-12345-xyz")
        self.login()
        r = self.api("post", "/me/email/", {"email": "BOB@example.com"})
        self.assertIn("Another account already uses", r.json()["fields"]["email"][0])
        r = self.api("post", "/me/email/", {"email": "alice.new@example.com"})
        self.assertEqual(r.json()["user"]["email"], "alice.new@example.com")
        self.assertEqual(User.objects.get(pk=self.user.pk).email, "alice.new@example.com")

    def test_data_export(self):
        self.login()
        self.api("post", "/venues/cvpr/star/")
        self.api("put", "/venues/cvpr/note/", {"note": "camera-ready tips"})
        r = self.client.get(reverse("accounts:export_data"))
        self.assertIn("attachment", r["Content-Disposition"])
        data = json.loads(r.content)
        self.assertEqual(data["account"]["username"], "alice")
        self.assertEqual(data["bookmarks"][0]["venue"], "cvpr")
        self.assertEqual(data["bookmarks"][0]["note"], "camera-ready tips")
        for key in ("profile", "venue_lists", "saved_searches", "papers", "reviews", "suggestions", "notifications"):
            self.assertIn(key, data)

    def test_delete_account_requires_password_and_confirmation(self):
        self.login()
        r = self.api("post", "/me/delete/", {"password": "wrong", "confirm": "DELETE"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Incorrect password", r.json()["fields"]["password"][0])
        r = self.api("post", "/me/delete/", {"password": "pw-12345-xyz", "confirm": "delete"})
        self.assertEqual(r.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        r = self.api("post", "/me/delete/", {"password": "pw-12345-xyz", "confirm": "DELETE"})
        self.assertFalse(r.json()["authenticated"])
        self.assertFalse(User.objects.filter(username="alice").exists())
        self.assertEqual(self.client.get(reverse("accounts:dashboard")).status_code, 302)

    def test_set_timezone(self):
        self.login()
        r = self.api("post", "/me/timezone/", {"timezone": "Asia/Dhaka"})
        self.assertEqual(r.json(), {"timezone": "Asia/Dhaka"})
        self.assertEqual(User.objects.get(pk=self.user.pk).profile.timezone, "Asia/Dhaka")
        self.assertEqual(self.api("post", "/me/timezone/", {"timezone": "Mars/Olympus"}).status_code, 400)
        self.assertEqual(self.client.get(f"{APP}/session/").json()["user"]["timezone"], "Asia/Dhaka")
        self.assertIn("Asia/Dhaka", self.client.get(f"{APP}/timezones/").json()["results"])

    def test_auth_next_is_safe(self):
        data = {"username": "carol", "email": "carol@example.com", "password1": "S3cure-pass-987", "password2": "S3cure-pass-987"}
        r = self.api("post", "/auth/signup/", {**data, "next": "https://evil.example.com/"})
        self.assertEqual(r.json()["next"], reverse("accounts:profile"))
        self.api("post", "/auth/logout/")
        r = self.api("post", "/auth/signup/", {**data, "username": "dave", "email": "dave@example.com", "next": "/targets/"})
        self.assertEqual(r.json()["next"], "/targets/")
        self.api("post", "/auth/logout/")
        r = self.api("post", "/auth/login/", {"username": "dave", "password": "S3cure-pass-987", "next": "//evil.example.com"})
        self.assertEqual(r.json()["next"], reverse("accounts:dashboard"))

    def test_auth_pages_are_noindex(self):
        r = self.client.get(reverse("accounts:login"))
        self.assertContains(r, '<meta name="robots" content="noindex">')
        self.assertContains(r, "<title>Log in · VenuePulse</title>")

    def test_initials(self):
        p = self.user.profile
        self.assertEqual(p.initials, "AL")
        p.display_name = "Ada Lovelace"
        self.assertEqual(p.initials, "AL")
        p.display_name = "grace"
        self.assertEqual(p.initials, "GR")


class EmailVerificationTests(AccountTestBase):
    def link_from(self, message):
        return next(line for line in message.body.splitlines() if "/accounts/verify/" in line).strip().split("testserver", 1)[1]

    def test_signup_sends_verification_and_link_confirms(self):
        self.api("post", "/auth/signup/", {"username": "newbie", "email": "newbie@example.com", "password1": "S3cure-pass-987", "password2": "S3cure-pass-987"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Confirm your email", mail.outbox[0].subject)
        user = User.objects.get(username="newbie")
        self.assertFalse(user.profile.email_verified)
        self.assertFalse(self.client.get(f"{APP}/session/").json()["user"]["email_verified"])
        r = self.client.get(self.link_from(mail.outbox[0]))
        self.assertRedirects(r, reverse("accounts:dashboard"), fetch_redirect_response=False)
        messages = boot_of(self.client.get(r["Location"]))["session"]["messages"]  # flash message shown as a toast
        self.assertIn("is confirmed", messages[0]["text"])
        user.profile.refresh_from_db()
        self.assertTrue(user.profile.email_verified)
        self.assertTrue(self.client.get(f"{APP}/session/").json()["user"]["email_verified"])

    def test_tampered_or_stale_tokens_are_rejected(self):
        from accounts.verification import make_token

        token = make_token(self.user)
        r = self.client.get(reverse("accounts:verify_email", args=[token[:-2] + "xx"]), follow=True)
        self.assertIn("invalid or has expired", boot_of(r)["session"]["messages"][0]["text"])
        self.user.email = "changed@example.com"
        self.user.save()
        r = self.client.get(reverse("accounts:verify_email", args=[token]), follow=True)  # token bound to the old address
        self.assertIn("invalid or has expired", boot_of(r)["session"]["messages"][0]["text"])
        self.assertFalse(User.objects.get(pk=self.user.pk).profile.email_verified)

    def test_email_change_invalidates_verification(self):
        p = self.user.profile
        p.verified_email = self.user.email
        p.save()
        self.login()
        self.api("post", "/me/email/", {"email": "alice2@example.com"})
        self.assertFalse(User.objects.get(pk=self.user.pk).profile.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("alice2@example.com", mail.outbox[0].to)

    def test_resend_is_rate_limited(self):
        from django.core.cache import cache
        from django.test import override_settings

        cache.clear()
        self.login()
        with override_settings(RATELIMIT_ENABLED=True):
            for _ in range(3):
                self.assertEqual(self.api("post", "/auth/verify-email/resend/").status_code, 200)
            limited = self.api("post", "/auth/verify-email/resend/")
            self.assertEqual(limited.status_code, 429)
            self.assertIn("retry_after", limited.json())
        self.assertEqual(len(mail.outbox), 3)

    def test_unverified_users_get_in_app_reminders_but_no_email(self):
        venue = Venue.objects.create(name="Soon", acronym="SOON2", slug="soon2", venue_type="Conference", primary_domain="X")
        DeadlineCycle.objects.create(venue=venue, year=2032, submission_deadline=timezone.now() + timedelta(days=3))
        VenueBookmark.objects.create(user=self.user, venue=venue)
        call_command("send_reminders", stdout=StringIO())
        self.assertEqual(self.user.notifications.count(), 1)
        self.assertEqual(len(mail.outbox), 0)
