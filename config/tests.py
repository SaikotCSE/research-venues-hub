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
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from config.env import env, env_bool, env_int, env_list, load_dotenv
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
        os.environ.update(VP_B="yes", VP_I="12", VP_L="a, b,,c", VP_EMPTY="")
        try:
            self.assertEqual(env("VP_EMPTY", "fallback"), "fallback", "empty counts as unset (CI passes VAR='')")
            self.assertEqual(env("VP_I", "x"), "12")
            self.assertTrue(env_bool("VP_B"))
            self.assertFalse(env_bool("VP_MISSING"))
            self.assertEqual(env_int("VP_I", 1), 12)
            self.assertEqual(env_int("VP_MISSING", 7), 7)
            self.assertEqual(env_list("VP_L"), ["a", "b", "c"])
        finally:
            for k in ("VP_B", "VP_I", "VP_L", "VP_EMPTY"):
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
            "check",
            "--deploy",
            "--fail-level",
            "WARNING",
            "--settings=config.settings.production",
            DJANGO_SECRET_KEY="x7!kP2#qL9$wZ4^mN8&vB3*cR6(tY1)uI5_oA0+sD7=fG2-hJ9~kL4",
            DJANGO_ALLOWED_HOSTS="venuepulse.example.com",
            SITE_URL="https://venuepulse.example.com",
            BREVO_API_KEY="placeholder",  # email must be configured (sign-up codes)
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_deploy_check_flags_missing_site_url(self):
        result = self.run_manage(
            "check",
            "--deploy",
            "--settings=config.settings.production",
            DJANGO_SECRET_KEY="x7!kP2#qL9$wZ4^mN8&vB3*cR6(tY1)uI5_oA0+sD7=fG2-hJ9~kL4",
            DJANGO_ALLOWED_HOSTS="venuepulse.example.com",
            SITE_URL="",
        )
        self.assertIn("venuepulse.W001", result.stdout + result.stderr)


class TemplateHygieneTests(SimpleTestCase):
    def test_no_inline_event_handlers_or_cdn_scripts(self):
        offenders = []
        for path in BASE_DIR.glob("**/templates/**/*.html"):
            if "node_modules" in path.parts or ".venv" in path.parts:
                continue
            text = path.read_text()
            if re.search(r"\son(click|change|submit|input|load|focus|keyup|keydown)=", text) or "cdn." in text or "unpkg.com" in text:
                offenders.append(str(path.relative_to(BASE_DIR)))
        self.assertEqual(offenders, [], "inline handlers break the CSP; keep behaviour in the React bundle or static files")

    def test_every_page_module_exists_in_the_build(self):
        from webapp import vite
        from webapp.views import PAGE_MODULES, PAGES

        manifest = vite.manifest()
        self.assertIn(vite.ENTRY, manifest)
        missing = [m for m in PAGE_MODULES.values() if f"frontend/src/{m}" not in manifest]
        self.assertEqual(missing, [], "run `npm run build` after adding pages")
        self.assertLessEqual(set(PAGE_MODULES), set(PAGES))


class SecurityHeaderTests(TestCase):
    def test_csp_nonce_matches_inline_script(self):
        r = self.client.get(reverse("venues:list"))
        csp = r["Content-Security-Policy"]
        nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
        self.assertIn(f'<script nonce="{nonce}">', r.content.decode())
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertNotIn("unsafe-eval", csp)
        self.assertIn("script-src 'self' 'nonce-", csp)
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
        from webapp import vite

        assets = vite.entry_assets(page_module="frontend/src/pages/explore.tsx")
        for url in (assets["script"], *assets["styles"], *assets["preloads"], "/static/venues/js/embed.js", "/static/venues/img/favicon.svg"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
        self.assertTrue(any("explore-" in p for p in assets["preloads"]), "the page's own chunk is preloaded")

    def test_custom_404(self):
        r = self.client.get("/definitely-not-here/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, '"page": "not_found"', status_code=404)
        self.assertContains(r, "<title>Page not found · VenuePulse</title>", status_code=404)
        api = self.client.get("/api/app/definitely-not-here/")
        self.assertEqual((api.status_code, api.json()), (404, {"error": "Not found."}))

    def test_missing_trailing_slash_redirects(self):
        r = self.client.get("/venue/neurips?x=1")
        self.assertEqual((r.status_code, r["Location"]), (301, "/venue/neurips/?x=1"))

    def test_csrf_failures_are_json_for_the_api(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        r = client.post("/api/app/venues/neurips/star/", data="{}", content_type="application/json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("CSRF", r.json()["error"])
        token = client.get("/api/app/session/").json()["csrf_token"]
        r = client.post("/api/app/venues/neurips/star/", data="{}", content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)

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
        url = "/api/app/auth/login/"
        body = '{"username": "rl", "password": "wrong"}'
        for _ in range(3):
            r = self.client.post(url, data=body, content_type="application/json")
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r["X-RateLimit-Limit"], "3")
        r = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(r.status_code, 429)
        self.assertIn("Retry-After", r)
        self.assertIn("Too many requests", r.json()["error"])
        self.assertEqual(self.client.get(reverse("accounts:login")).status_code, 200, "the page itself is not limited")

    @override_settings(RATELIMIT_ENABLED=True, RATELIMITS={**settings.RATELIMITS, "api_public": "2/m"})
    def test_api_limit_returns_json(self):
        for _ in range(2):
            self.assertEqual(self.client.get(reverse("venues:api_venues")).status_code, 200)
        r = self.client.get(reverse("venues:api_venues"))
        self.assertEqual(r.status_code, 429)
        self.assertIn("retry_after", r.json())


class CompressionTests(TestCase):
    def test_html_and_json_are_gzipped(self):
        call_command("seed_venues", verbosity=0)
        r = self.client.get(reverse("venues:list"), HTTP_ACCEPT_ENCODING="gzip")
        self.assertEqual(r["Content-Encoding"], "gzip")
        self.assertIn("Accept-Encoding", r["Vary"])
        self.assertLess(len(r.content), 60_000)
        self.assertEqual(self.client.get(reverse("venues:api_venues"), HTTP_ACCEPT_ENCODING="gzip")["Content-Encoding"], "gzip")


class BrevoBackendTests(SimpleTestCase):
    def send(self, **kwargs):
        from unittest import mock

        from django.core.mail import EmailMultiAlternatives

        from config.mail import BrevoEmailBackend

        message = EmailMultiAlternatives("Hi", "plain body", "VenuePulse <venupulse@example.com>", ["Ada <ada@example.com>", "bob@example.com"], **kwargs)
        message.attach_alternative("<p>html body</p>", "text/html")
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b'{"messageId": "x"}'
            sent = BrevoEmailBackend(api_key="secret-key").send_messages([message])
        return sent, urlopen

    def test_posts_the_message_as_json(self):
        sent, urlopen = self.send(reply_to=["help@example.com"])
        self.assertEqual(sent, 1)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(request.get_header("Api-key"), "secret-key")
        body = __import__("json").loads(request.data)
        self.assertEqual(body["sender"], {"email": "venupulse@example.com", "name": "VenuePulse"})
        self.assertEqual(body["to"], [{"email": "ada@example.com", "name": "Ada"}, {"email": "bob@example.com"}])
        self.assertEqual((body["subject"], body["textContent"], body["htmlContent"]), ("Hi", "plain body", "<p>html body</p>"))
        self.assertEqual(body["replyTo"], {"email": "help@example.com"})

    def test_api_errors_raise_unless_silenced(self):
        import io
        import urllib.error
        from unittest import mock

        from django.core.mail import EmailMessage

        from config.mail import BrevoEmailBackend

        error = urllib.error.HTTPError("https://api.brevo.com", 401, "Unauthorized", {}, io.BytesIO(b'{"message":"Key not found"}'))
        message = EmailMessage("Hi", "body", "a@example.com", ["b@example.com"])
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesMessage(RuntimeError, "HTTP 401"):
                BrevoEmailBackend(api_key="k").send_messages([message])
            self.assertEqual(BrevoEmailBackend(api_key="k", fail_silently=True).send_messages([message]), 0)


class EmailDeployCheckTests(SimpleTestCase):
    def test_warns_when_email_only_goes_to_the_console(self):
        from config.checks import check_email_backend

        with override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"):
            self.assertEqual([w.id for w in check_email_backend(None)], ["venuepulse.W003"])
        with override_settings(EMAIL_BACKEND="config.mail.BrevoEmailBackend"):
            self.assertEqual(check_email_backend(None), [])
