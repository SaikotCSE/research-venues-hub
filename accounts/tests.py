import json
import re
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import EmailCode, Notification, SavedSearch, VenueList
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

    @staticmethod
    def last_code():
        """The one-time code in the most recent email."""
        return re.search(r"^ +(\d{6})$", mail.outbox[-1].body, re.M).group(1)

    def signup_and_verify(self, client=None, **data):
        r = self.api("post", "/auth/signup/", data, client=client)
        self.assertEqual(r.status_code, 200, r.content)
        return self.api("post", "/auth/signup/verify/", {"code": self.last_code(), "next": data.get("next")}, client=client)


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
        self.assertEqual({k: r.json()[k] for k in ("email", "expires_in", "resend_in")}, {"email": "bob@example.com", "expires_in": 600, "resend_in": 60})
        self.assertFalse(User.objects.filter(username="bob").exists(), "no account until the code is confirmed")
        self.assertFalse(self.client.get(f"{APP}/session/").json()["authenticated"])
        self.assertEqual(mail.outbox[0].to, ["bob@example.com"])
        code = self.last_code()
        self.assertTrue(mail.outbox[0].subject.startswith(code))

        data = self.api("post", "/auth/signup/verify/", {"code": code}).json()
        self.assertTrue(data["authenticated"])
        self.assertEqual((data["user"]["username"], data["next"]), ("bob", reverse("accounts:profile")))
        self.assertTrue(data["user"]["email_verified"], "the code confirmed the address")
        self.assertTrue(User.objects.get(username="bob").check_password("S3cure-pass-987"))
        self.assertFalse(EmailCode.objects.exists(), "used codes are deleted")
        self.api("post", "/auth/logout/")
        self.assertEqual(self.api("post", "/auth/signup/verify/", {"code": code}).status_code, 400, "a code works once")

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

    def test_signup_keeps_anonymous_stars(self):
        venue = Venue.objects.first()
        self.client.post(f"{APP}/venues/{venue.slug}/star/", content_type="application/json")
        self.signup_and_verify(username="erin", email="erin@example.com", password1="S3cure-pass-987", password2="S3cure-pass-987")
        self.assertTrue(VenueBookmark.objects.filter(user__username="erin", venue=venue, is_starred=True).exists())

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

    def test_tokens_and_feed_links_never_reach_the_browser(self):
        self.login()
        p = self.user.profile
        for body in (self.client.get(f"{APP}/me/profile/").content, self.client.get(f"{APP}/me/dashboard/").content):
            for secret in (p.api_token, p.calendar_token, "api_token", "calendar_url"):
                self.assertNotIn(secret.encode(), body)
        self.assertEqual(self.api("post", "/me/tokens/api/").status_code, 404, "no regenerate endpoint")

    def test_api_tokens_are_stored_hashed(self):
        from accounts.models import hash_token

        p = self.user.profile
        self.assertEqual(len(p.api_token), 64, "new profiles start with a hash of a token nobody knows")
        token = p.issue_api_token()
        p.refresh_from_db()
        self.assertEqual(p.api_token, hash_token(token))
        self.assertNotIn(token, p.api_token)
        self.assertEqual(self.client.get(reverse("venues:api_me"), HTTP_AUTHORIZATION=f"Bearer {token}").status_code, 200)
        self.assertEqual(self.client.get(reverse("venues:api_me"), HTTP_AUTHORIZATION=f"Bearer {p.api_token}").status_code, 401, "the hash is not a token")
        self.assertEqual(self.client.get(reverse("venues:api_me"), HTTP_AUTHORIZATION="Bearer ").status_code, 401)

    def test_migration_hashes_existing_plain_tokens(self):
        import importlib

        from django.apps import apps

        from accounts.models import UserProfile, hash_token

        migration = importlib.import_module("accounts.migrations.0006_hash_api_tokens")
        UserProfile.objects.filter(pk=self.user.profile.pk).update(api_token="old-plain-token-copied-by-a-user")
        migration.hash_existing_tokens(apps, None)
        migration.hash_existing_tokens(apps, None)  # running twice doesn't hash twice
        stored = UserProfile.objects.get(pk=self.user.profile.pk).api_token
        self.assertEqual(stored, hash_token("old-plain-token-copied-by-a-user"))
        r = self.client.get(reverse("venues:api_me"), HTTP_AUTHORIZATION="Bearer old-plain-token-copied-by-a-user")
        self.assertEqual(r.status_code, 200, "a token copied before the change keeps working")

    def test_issue_api_token_command(self):
        out, err = StringIO(), StringIO()
        call_command("issue_api_token", "alice", stdout=out, stderr=err)
        token = out.getvalue().strip()
        self.assertEqual(self.client.get(reverse("venues:api_me"), HTTP_AUTHORIZATION=f"Bearer {token}").json()["username"], "alice")
        self.assertIn("can't be shown again", err.getvalue())
        call_command("issue_api_token", "alice", stdout=StringIO(), stderr=StringIO())
        self.assertEqual(self.client.get(reverse("venues:api_me"), HTTP_AUTHORIZATION=f"Bearer {token}").status_code, 401, "the old token is revoked")
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("issue_api_token", "nobody", stdout=StringIO(), stderr=StringIO())


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
    def reset_confirm(self, code, password="Brand-new-pass-77", confirm=None):
        return self.api("post", "/auth/password-reset/confirm/", {"code": code, "new_password1": password, "new_password2": confirm or password})

    def test_password_reset_end_to_end(self):
        other = Client()  # a session that was signed in before the reset
        other.force_login(self.user)
        r = self.api("post", "/auth/password-reset/", {"email": "ALICE@example.com"})
        self.assertEqual(r.json()["email"], "alice@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("password reset code", mail.outbox[0].subject)
        code = self.last_code()
        self.assertEqual(self.reset_confirm(code, "short").status_code, 400)  # a weak password doesn't use up the code
        self.assertEqual(self.reset_confirm(code).json(), {"ok": True})
        self.assertTrue(self.client.login(username="alice", password="Brand-new-pass-77"))
        self.assertEqual(other.get(f"{APP}/me/dashboard/").status_code, 401, "other sessions are signed out")
        self.assertEqual(self.reset_confirm(code, "Other-pass-777").status_code, 400, "a code works once")

    def test_password_reset_unknown_email_is_silent(self):
        known = self.api("post", "/auth/password-reset/", {"email": "alice@example.com"}, client=Client()).json()
        unknown = self.api("post", "/auth/password-reset/", {"email": "nobody@example.com"}).json()
        self.assertEqual(unknown.keys(), known.keys())
        self.assertEqual(unknown["message"], known["message"].replace("alice@", "nobody@"))
        self.assertEqual(len(mail.outbox), 1, "only the real account gets an email")
        r = self.reset_confirm("123456")
        self.assertEqual(r.status_code, 400)
        self.assertIn("incorrect", r.json()["fields"]["code"][0])
        again = self.api("post", "/auth/password-reset/", {"email": "nobody@example.com"})
        self.assertEqual(again.status_code, 429, "the resend cooldown applies whether or not the account exists")

    def test_password_reset_ignores_inactive_accounts(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.api("post", "/auth/password-reset/", {"email": "alice@example.com"}).status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_needs_a_valid_email(self):
        r = self.api("post", "/auth/password-reset/", {"email": "not-an-email"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.json()["fields"])

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
        r = self.signup_and_verify(**data, next="https://evil.example.com/")
        self.assertEqual(r.json()["next"], reverse("accounts:profile"))
        self.api("post", "/auth/logout/")
        r = self.signup_and_verify(**{**data, "username": "dave", "email": "dave@example.com"}, next="/targets/")
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

    def test_verification_link_confirms(self):
        """Accounts created before sign-up codes (and changed addresses) still confirm through a link."""
        from accounts.verification import send_verification_email

        user = self.user
        self.login()
        self.assertFalse(self.client.get(f"{APP}/session/").json()["user"]["email_verified"])
        send_verification_email(user)
        self.assertIn("Confirm your email", mail.outbox[0].subject)
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


class EmailCodeTests(AccountTestBase):
    """The one-time codes behind sign-up and password reset (accounts/otp.py)."""

    DATA = {"username": "bob", "email": "bob@example.com", "password1": "S3cure-pass-987", "password2": "S3cure-pass-987"}

    def start(self, client=None, **overrides):
        r = self.api("post", "/auth/signup/", {**self.DATA, **overrides}, client=client)
        self.assertEqual(r.status_code, 200, r.content)
        return self.last_code()

    def verify(self, code, client=None):
        return self.api("post", "/auth/signup/verify/", {"code": code}, client=client)

    def wrong(self, code):
        return f"{(int(code) + 1) % 1_000_000:06d}"

    def age(self, **delta):
        """Pretend the current code was sent (and expires) ``delta`` earlier."""
        row = EmailCode.objects.get()
        shift = timedelta(**delta)
        EmailCode.objects.filter(pk=row.pk).update(
            sent_at=row.sent_at - shift, expires_at=row.expires_at - shift, window_started_at=row.window_started_at - shift
        )

    def test_only_a_hash_is_stored(self):
        code = self.start()
        row = EmailCode.objects.get()
        self.assertEqual((row.purpose, row.email, row.attempts, row.sends), ("signup", "bob@example.com", 0, 1))
        self.assertNotIn(code, json.dumps([row.code_hash, row.flow, row.payload]))
        self.assertNotIn("S3cure-pass-987", json.dumps(row.payload), "the password is stored hashed")

    def test_wrong_codes_are_counted_and_lock_the_code(self):
        code = self.start()
        r = self.verify(self.wrong(code))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["fields"]["code"], ["That code is incorrect. 4 attempts left."])
        for _ in range(4):
            self.verify(self.wrong(code))
        r = self.verify(code)
        self.assertIn("Too many incorrect attempts", r.json()["error"])
        self.assertFalse(User.objects.filter(username="bob").exists())

    def test_malformed_codes_do_not_use_an_attempt(self):
        self.start()
        for bad in ("", "12345", "abcdef", "1234567", "١٢٣٤٥٦"):
            r = self.verify(bad)
            self.assertEqual(r.json()["fields"]["code"], ["Enter the 6-digit code from the email."], bad)
        self.assertEqual(EmailCode.objects.get().attempts, 0)

    def test_spaces_and_dashes_in_the_code_are_ignored(self):
        code = self.start()
        self.assertTrue(self.verify(f" {code[:3]}-{code[3:]} ").json()["authenticated"])

    def test_codes_expire(self):
        code = self.start()
        self.age(minutes=11)
        self.assertIn("expired", self.verify(code).json()["error"])

    def test_code_only_works_in_the_browser_that_asked(self):
        code = self.start()
        self.assertIn("expired", self.verify(code, client=Client()).json()["error"])
        self.assertTrue(self.verify(code).json()["authenticated"])

    def test_resend_cooldown_and_new_code(self):
        first = self.start()
        r = self.api("post", "/auth/code/resend/", {"purpose": "signup"})
        self.assertEqual(r.status_code, 429)
        self.assertIn("Please wait", r.json()["error"])
        self.age(seconds=61)
        r = self.api("post", "/auth/code/resend/", {"purpose": "signup"})
        self.assertEqual(r.status_code, 200)
        second = self.last_code()
        self.assertEqual(len(mail.outbox), 2)
        if second != first:  # (one in a million they match)
            self.assertIn("incorrect", self.verify(first).json()["error"], "the old code stops working")
        self.assertTrue(self.verify(second).json()["authenticated"])

    def test_sends_per_address_are_capped(self):
        self.start()
        for _ in range(4):
            self.age(seconds=61)
            self.assertEqual(self.api("post", "/auth/code/resend/", {"purpose": "signup"}).status_code, 200)
        self.age(seconds=61)
        r = self.api("post", "/auth/code/resend/", {"purpose": "signup"})
        self.assertEqual(r.status_code, 429)
        self.assertIn("Too many codes", r.json()["error"])
        self.age(hours=1)
        self.assertEqual(self.api("post", "/auth/code/resend/", {"purpose": "signup"}).status_code, 200, "the window resets")

    def test_another_browser_signing_up_with_the_same_address_waits_too(self):
        self.start()
        r = self.api("post", "/auth/signup/", self.DATA, client=Client())
        self.assertEqual(r.status_code, 429)

    def test_resend_without_a_pending_code(self):
        self.assertEqual(self.api("post", "/auth/code/resend/", {"purpose": "signup"}).status_code, 400)
        self.assertEqual(self.api("post", "/auth/code/resend/", {"purpose": "nope"}).status_code, 400)

    def test_username_taken_while_confirming(self):
        code = self.start()
        User.objects.create_user("Bob", "someone@example.com", "pw-12345-xyz")
        r = self.verify(code)
        self.assertEqual(r.status_code, 409)
        self.assertFalse(EmailCode.objects.exists())

    def test_email_failure_reports_an_error_and_allows_a_retry(self):
        with mock.patch("accounts.otp.send_mail", side_effect=OSError("smtp down")):
            r = self.api("post", "/auth/signup/", self.DATA)
        self.assertEqual(r.status_code, 503)
        self.assertFalse(EmailCode.objects.exists())
        self.start()  # no cooldown after a failed send

    def test_signed_in_users_cannot_sign_up(self):
        self.login()
        self.assertEqual(self.api("post", "/auth/signup/", self.DATA).status_code, 400)
        self.assertEqual(self.verify("123456").status_code, 400)

    def test_reset_code_is_void_if_the_email_changed(self):
        self.api("post", "/auth/password-reset/", {"email": "alice@example.com"})
        code = self.last_code()
        User.objects.filter(pk=self.user.pk).update(email="new@example.com")
        r = self.api("post", "/auth/password-reset/confirm/", {"code": code, "new_password1": "Brand-new-pass-77", "new_password2": "Brand-new-pass-77"})
        self.assertIn("no longer valid", r.json()["error"])
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password("pw-12345-xyz"))

    def test_signup_and_reset_codes_are_separate(self):
        self.api("post", "/auth/password-reset/", {"email": "alice@example.com"})
        code = self.last_code()
        self.assertIn("expired", self.verify(code).json()["error"])
