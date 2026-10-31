import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from config.env import env_bool, env_int, env_list, load_dotenv
from config.ratelimit import parse_rate

BASE_DIR = Path(settings.BASE_DIR)


class EnvHelperTests(SimpleTestCase):
    def test_load_dotenv_does_not_override(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as fh:
            fh.write("# comment\nVP_TEST_A=1\nexport VP_TEST_B='quoted value'\nVP_TEST_C=\"x\"\nnot a pair\n")
        os.environ["VP_TEST_C"] = "real"
        try:
            load_dotenv(Path(fh.name))
            self.assertEqual(os.environ["VP_TEST_A"], "1")
            self.assertEqual(os.environ["VP_TEST_B"], "quoted value")
            self.assertEqual(os.environ["VP_TEST_C"], "real")
        finally:
            for k in ("VP_TEST_A", "VP_TEST_B", "VP_TEST_C"):
                os.environ.pop(k, None)
            os.unlink(fh.name)

    def test_typed_helpers(self):
        os.environ.update(VP_B="yes", VP_I="12", VP_L="a, b,,c")
        try:
            self.assertTrue(env_bool("VP_B"))
            self.assertFalse(env_bool("VP_MISSING"))
            self.assertEqual(env_int("VP_I", 1), 12)
            self.assertEqual(env_int("VP_MISSING", 7), 7)
            self.assertEqual(env_list("VP_L"), ["a", "b", "c"])
        finally:
            for k in ("VP_B", "VP_I", "VP_L"):
                os.environ.pop(k)

    def test_parse_rate(self):
        self.assertEqual(parse_rate("10/m"), (10, 60))
        self.assertEqual(parse_rate("5/hour"), (5, 3600))


class ProductionSettingsTests(SimpleTestCase):
    """Run in a subprocess so production settings never leak into this test process."""

    def run_manage(self, *args, **env):
        full_env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
        full_env.update(env)
        return subprocess.run([sys.executable, "manage.py", *args], cwd=BASE_DIR, env=full_env, capture_output=True, text=True, timeout=120)

    def test_requires_secret_key(self):
        result = self.run_manage("check", "--settings=config.settings.production", DJANGO_SECRET_KEY="")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY must be set", result.stderr)

    def test_deploy_check_is_clean(self):
        result = self.run_manage(
            "check", "--deploy", "--fail-level", "WARNING", "--settings=config.settings.production",
            DJANGO_SECRET_KEY="x7!kP2#qL9$wZ4^mN8&vB3*cR6(tY1)uI5_oA0+sD7=fG2-hJ9~kL4", DJANGO_ALLOWED_HOSTS="venuepulse.example.com",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)


class IconTagTests(SimpleTestCase):
    def test_icon_renders_sprite_reference(self):
        html = Template('{% icon "search" "h-5 w-5" %}').render(Context())
        self.assertIn('aria-hidden="true"', html)
        self.assertIn("venues/img/icons.svg#search", html)
        labelled = Template('{% icon "bell" label="Alerts" %}').render(Context())
        self.assertIn('role="img"', labelled)
        self.assertIn('aria-label="Alerts"', labelled)

    def test_every_icon_used_in_templates_exists_in_sprite(self):
        sprite = (BASE_DIR / "venues/static/venues/img/icons.svg").read_text()
        available = set(re.findall(r'<symbol id="([a-z0-9-]+)"', sprite))
        used = set()
        for path in BASE_DIR.glob("**/templates/**/*.html"):
            if "node_modules" in path.parts or ".venv" in path.parts:
                continue
            used |= set(re.findall(r'\{%\s*icon\s+"([a-z0-9-]+)"', path.read_text()))
        self.assertTrue(used)
        self.assertEqual(sorted(used - available), [], "run `npm run build:icons` after adding icons")

    def test_no_inline_event_handlers_or_cdn_scripts(self):
        offenders = []
        for path in BASE_DIR.glob("**/templates/**/*.html"):
            if "node_modules" in path.parts or ".venv" in path.parts:
                continue
            text = path.read_text()
            if re.search(r"\son(click|change|submit|input|load|focus|keyup|keydown)=", text) or "cdn." in text or "unpkg.com" in text:
                offenders.append(str(path.relative_to(BASE_DIR)))
        self.assertEqual(offenders, [], "inline handlers break the CSP; use Alpine (@click etc.) and local static files")


class SecurityHeaderTests(TestCase):
    def test_csp_nonce_matches_inline_script(self):
        r = self.client.get(reverse("venues:list"))
        csp = r["Content-Security-Policy"]
        nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
        self.assertIn(f'<script nonce="{nonce}">', r.content.decode())
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertNotEqual(nonce, re.search(r"'nonce-([^']+)'", self.client.get(reverse("venues:list"))["Content-Security-Policy"]).group(1))

    @override_settings(CSP_REPORT_ONLY=True)
    def test_report_only_mode(self):
        r = self.client.get(reverse("venues:list"))
        self.assertIn("Content-Security-Policy-Report-Only", r)
        self.assertNotIn("Content-Security-Policy", r)

    def test_other_headers(self):
        r = self.client.get(reverse("venues:list"))
        self.assertIn("camera=()", r["Permissions-Policy"])
        self.assertEqual(r["X-Frame-Options"], "DENY")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertRegex(r["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_request_id_is_propagated_when_sane(self):
        self.assertEqual(self.client.get("/healthz", HTTP_X_REQUEST_ID="abc-123")["X-Request-ID"], "abc-123")
        self.assertNotEqual(self.client.get("/healthz", HTTP_X_REQUEST_ID="bad id <script>")["X-Request-ID"], "bad id <script>")


class OpsEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def test_healthz(self):
        r = self.client.get("/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "database": "ok", "cache": "ok"})
        self.assertIn("no-store", r["Cache-Control"])

    def test_robots_and_sitemap(self):
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /accounts/", robots)
        self.assertIn("Sitemap: http://testserver/sitemap.xml", robots)
        cache.clear()
        sitemap = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("http://testserver/venue/neurips/", sitemap)
        self.assertIn("<lastmod>", sitemap)
        self.assertIn("http://testserver/recommend/", sitemap)

    def test_manifest_and_favicon(self):
        r = self.client.get("/manifest.webmanifest")
        self.assertEqual(r["Content-Type"], "application/manifest+json")
        self.assertEqual(r.json()["short_name"], "VenuePulse")
        self.assertEqual(self.client.get("/favicon.ico").status_code, 301)

    def test_static_assets_are_served(self):
        for path in ("venues/css/app.css", "venues/js/app.js", "venues/vendor/htmx.min.js", "venues/vendor/alpine.min.js", "venues/img/icons.svg"):
            r = self.client.get(f"/static/{path}")
            self.assertEqual(r.status_code, 200, path)

    def test_custom_404(self):
        r = self.client.get("/definitely-not-here/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "We couldn’t find that page", status_code=404)

    def test_canonical_and_open_graph(self):
        r = self.client.get(reverse("venues:detail", args=["neurips"]))
        self.assertContains(r, '<link rel="canonical" href="http://testserver/venue/neurips/">')
        self.assertContains(r, 'property="og:image"')


class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("rl", "rl@example.com", "pw-12345-xyz")

    @override_settings(RATELIMIT_ENABLED=True, RATELIMITS={**settings.RATELIMITS, "login": "3/m"})
    def test_login_is_rate_limited(self):
        url = reverse("accounts:login")
        for _ in range(3):
            r = self.client.post(url, {"username": "rl", "password": "wrong"})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r["X-RateLimit-Limit"], "3")
        r = self.client.post(url, {"username": "rl", "password": "wrong"})
        self.assertEqual(r.status_code, 429)
        self.assertIn("Retry-After", r)
        self.assertContains(r, "Too many requests", status_code=429)
        self.assertEqual(self.client.get(url).status_code, 200, "GETs are not limited")

    @override_settings(RATELIMIT_ENABLED=True, RATELIMITS={**settings.RATELIMITS, "api_public": "2/m"})
    def test_api_limit_returns_json(self):
        for _ in range(2):
            self.assertEqual(self.client.get(reverse("venues:api_venues")).status_code, 200)
        r = self.client.get(reverse("venues:api_venues"))
        self.assertEqual(r.status_code, 429)
        self.assertIn("retry_after", r.json())
