import json

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from venues.models import Venue


def boot_of(response):
    return json.loads(response.content.decode().split('id="vp-boot" type="application/json">')[1].split("</script>")[0])


class ShellTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def test_public_pages_render_with_their_own_titles(self):
        pages = {
            "venues:list": "VenuePulse · Conference &amp; journal deadlines with live countdowns",
            "venues:compare": "Compare venues · VenuePulse",
            "venues:targets": "My target venues · VenuePulse",
            "venues:recommend": "Venue recommender · VenuePulse",
            "venues:plan": "Deadline planner · VenuePulse",
            "venues:insights": "Insights · VenuePulse",
            "venues:api_docs": "API documentation · VenuePulse",
            "community:changes": "Deadline radar · VenuePulse",
            "about": "About &amp; FAQ · VenuePulse",
            "privacy": "Privacy · VenuePulse",
            "accounts:login": "Log in · VenuePulse",
            "accounts:signup": "Create your account · VenuePulse",
            "accounts:password_reset": "Reset your password · VenuePulse",
        }
        for name, title in pages.items():
            r = self.client.get(reverse(name))
            self.assertContains(r, f"<title>{title}</title>", msg_prefix=name)
            self.assertContains(r, '<script type="module" src="/static/webapp/assets/main-', msg_prefix=name)

    def test_private_and_utility_pages_are_noindex(self):
        self.assertContains(self.client.get(reverse("venues:targets")), '<meta name="robots" content="noindex">')
        self.assertNotContains(self.client.get(reverse("venues:list")), 'name="robots"')

    def test_signed_in_pages(self):
        user = User.objects.create_user("zoe", "zoe@example.com", "pw-12345-xyz")
        for name in (
            "accounts:dashboard",
            "accounts:profile",
            "accounts:settings",
            "accounts:notifications",
            "accounts:lists",
            "tracker:board",
            "tracker:papers",
        ):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)
        self.client.force_login(user)
        for name in (
            "accounts:dashboard",
            "accounts:profile",
            "accounts:settings",
            "accounts:notifications",
            "accounts:lists",
            "tracker:board",
            "tracker:papers",
        ):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)
            self.assertTrue(boot_of(r)["session"]["authenticated"])

    def test_boot_data_is_escaped(self):
        Venue.objects.filter(slug="cvpr").update(description="</script><script>alert(1)</script>")
        html = self.client.get(reverse("venues:detail", args=["cvpr"])).content.decode()
        self.assertNotIn("</script><script>alert(1)", html)
        self.assertIn("\\u003C/script\\u003E\\u003Cscript\\u003Ealert(1)", html)

    def test_explore_shell_embeds_the_requested_view(self):
        boot = boot_of(self.client.get(reverse("venues:list"), {"view": "timeline", "type": "Conference"}))
        self.assertIn("rows", boot["initial"]["explore"])
        boot = boot_of(self.client.get(reverse("venues:list"), {"view": "calendar"}))
        self.assertEqual(len(boot["initial"]["explore"]["months"]), 12)

    def test_canonical_ignores_filters(self):
        r = self.client.get(reverse("venues:list"), {"core": "A*"})
        self.assertContains(r, '<link rel="canonical" href="http://testserver/">')

    @override_settings(VITE_DEV_SERVER_URL="http://localhost:5173")
    def test_dev_server_mode(self):
        html = self.client.get(reverse("about")).content.decode()
        self.assertIn('<script type="module" src="http://localhost:5173/@vite/client"></script>', html)
        self.assertIn('src="http://localhost:5173/frontend/src/main.tsx"', html)
        self.assertNotIn("/static/webapp/assets/", html)

    def test_missing_manifest_has_a_helpful_error(self):
        from pathlib import Path
        from unittest import mock

        from webapp import vite

        with mock.patch.object(vite, "MANIFEST", Path("/nonexistent/manifest.json")), self.assertRaisesMessage(vite.ViteManifestError, "npm run build"):
            vite.entry_assets()
