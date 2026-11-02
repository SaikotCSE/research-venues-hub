import json

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class PublicApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def test_pagination_links(self):
        r = self.client.get(reverse("venues:api_venues"), {"page_size": 10, "type": "Conference"}).json()
        self.assertEqual((r["page"], r["page_size"]), (1, 10))
        self.assertIsNone(r["previous"])
        self.assertTrue(r["next"].startswith("http://testserver/api/venues/?"))
        self.assertIn("type=Conference", r["next"])
        nxt = self.client.get(r["next"]).json()
        self.assertEqual(nxt["page"], 2)
        self.assertIsNotNone(nxt["previous"])
        self.assertTrue({v["slug"] for v in r["results"]}.isdisjoint(v["slug"] for v in nxt["results"]))

    def test_every_venue_has_canonical_url(self):
        r = self.client.get(reverse("venues:api_venue_detail", args=["neurips"])).json()
        self.assertEqual(r["url"], "http://testserver/venue/neurips/")
        self.assertIn("verified_at", r["cycles"][0])

    def test_etag_and_304(self):
        url = reverse("venues:api_venues")
        r = self.client.get(url, {"q": "vision"})
        etag = r["ETag"]
        self.assertTrue(etag.startswith('W/"'))
        self.assertIn("max-age=300", r["Cache-Control"])
        r2 = self.client.get(url, {"q": "vision"}, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(r2.status_code, 304)
        self.assertNotEqual(self.client.get(url, {"q": "nature"})["ETag"], etag, "different query, different ETag")

    def test_etag_changes_when_catalogue_changes(self):
        from .models import Venue

        url = reverse("venues:api_venue_detail", args=["cvpr"])
        etag = self.client.get(url)["ETag"]
        Venue.objects.filter(slug="cvpr").first().save()
        self.assertEqual(self.client.get(url, HTTP_IF_NONE_MATCH=etag).status_code, 200)

    def test_cors_and_preflight(self):
        r = self.client.get(reverse("venues:api_tags"))
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")
        self.assertIn("ETag", r["Access-Control-Expose-Headers"])
        pre = self.client.options(reverse("venues:api_venues"))
        self.assertEqual(pre.status_code, 204)
        self.assertEqual(pre["Access-Control-Allow-Origin"], "*")

    def test_json_errors(self):
        r = self.client.get(reverse("venues:api_venue_detail", args=["nope"]))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["error"], "No venue with slug 'nope'.")
        r = self.client.post(reverse("venues:api_venues"))
        self.assertEqual(r.status_code, 405)
        self.assertEqual(r["Allow"], "GET")
        self.assertIn("not allowed", r.json()["error"])

    def test_page_size_bounds(self):
        self.assertEqual(self.client.get(reverse("venues:api_venues"), {"page_size": 1000}).json()["page_size"], 200)
        self.assertEqual(self.client.get(reverse("venues:api_venues"), {"page_size": "0"}).json()["page_size"], 1)
        last = self.client.get(reverse("venues:api_venues"), {"page": 999}).json()
        self.assertEqual(last["page"], last["num_pages"])

    def test_insights_cached_and_stamped(self):
        d = self.client.get(reverse("venues:api_insights")).json()
        self.assertIn("generated_at", d)
        self.assertEqual(self.client.get(reverse("venues:api_insights")).json()["generated_at"], d["generated_at"])

    def test_openapi_schema(self):
        r = self.client.get(reverse("venues:openapi"))
        schema = r.json()
        self.assertEqual(schema["openapi"], "3.1.0")
        for path in ("/api/venues/", "/api/venues/{slug}/", "/api/v1/me/targets/", "/api/v1/me/targets/{slug}/"):
            self.assertIn(path, schema["paths"])
        self.assertIn("bearerAuth", schema["components"]["securitySchemes"])
        self.assertIn("next", schema["components"]["schemas"]["VenuePage"]["properties"])
        self.assertEqual(schema["servers"][0]["url"], "http://testserver")

    def test_docs_page(self):
        self.assertContains(self.client.get(reverse("venues:api_docs")), "<title>API documentation · VenuePulse</title>")
        meta = self.client.get("/api/app/api-meta/").json()
        self.assertEqual(meta["host"], "http://testserver")
        self.assertIn("/api/openapi.json", [e["path"] for g in meta["groups"] for e in g["endpoints"]])
        self.assertEqual(set(meta["limits"]) >= {"api_public", "api_token"}, True)


class TokenApiErrorTests(TestCase):
    def test_401_has_www_authenticate(self):
        r = self.client.get(reverse("venues:api_me"))
        self.assertEqual(r.status_code, 401)
        self.assertIn("Bearer", r["WWW-Authenticate"])

    def test_inactive_user_token_rejected(self):
        u = User.objects.create_user("x", "x@example.com", "pw-12345-xyz", is_active=False)
        r = self.client.get(reverse("venues:api_me"), HTTP_AUTHORIZATION=f"Bearer {u.profile.api_token}")
        self.assertEqual(r.status_code, 401)

    def test_token_endpoints_are_not_cors_enabled(self):
        u = User.objects.create_user("y", "y@example.com", "pw-12345-xyz")
        r = self.client.get(reverse("venues:api_me"), HTTP_AUTHORIZATION=f"Bearer {u.profile.api_token}")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", r)
        bad = self.client.post(
            reverse("venues:api_me_targets"), json.dumps({"slug": "nope"}), content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {u.profile.api_token}"
        )
        self.assertEqual(bad.status_code, 404)
        self.assertIn("error", bad.json())
