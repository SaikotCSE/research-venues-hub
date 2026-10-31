import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import VenueBookmark
from .recommend import plan, recommend, tokens


class RecommenderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def test_tokens(self):
        self.assertEqual(tokens("The Medical-Image segmentation of 3D scans!"), ["medical-image", "segmentation", "3d", "scans"])

    def top(self, text, n=5, **kw):
        return [r["venue"].acronym for r in recommend(text, limit=n, **kw)]

    def test_medical_imaging_query(self):
        top = self.top("deep learning segmentation of medical images")
        self.assertTrue({"MICCAI", "MIDL", "MedIA", "IEEE TMI"} & set(top), top)

    def test_security_query(self):
        top = self.top("privacy preserving applied cryptography for systems security", 8)
        self.assertTrue({"IEEE S&P", "USENIX Security", "CCS", "NDSS"} & set(top), top)

    def test_nlp_query_respects_filters(self):
        res = recommend("large language models machine translation", venue_type="Journal", limit=10)
        self.assertTrue(res and all(r["venue"].venue_type == "Journal" for r in res))
        res = recommend("large language models", domain="Natural Language Processing", limit=10)
        self.assertTrue(res and all(r["venue"].primary_domain == "Natural Language Processing" for r in res))

    def test_scores_normalised_and_sorted(self):
        res = recommend("reinforcement learning robotics", limit=10)
        self.assertEqual(res[0]["percent"], 100)
        self.assertEqual([r["score"] for r in res], sorted((r["score"] for r in res), reverse=True))
        self.assertTrue(all(r["reasons"] is not None for r in res))

    def test_empty_and_stopword_only_queries(self):
        self.assertEqual(recommend(""), [])
        self.assertEqual(recommend("the and of"), [])
        self.assertEqual(recommend("zzzxqv qqqwww"), [])

    def test_only_with_deadline(self):
        res = recommend("neural networks", only_with_deadline=True, limit=50)
        self.assertTrue(all(r["next"] or r["venue"].is_rolling_submission for r in res))

    def test_recommend_page(self):
        r = self.client.get(reverse("venues:recommend"), {"text": "graph neural networks for recommender systems"})
        self.assertContains(r, "match")
        self.assertTrue(r.context["results"])
        self.assertContains(self.client.get(reverse("venues:recommend")), "Where should I submit?")
        self.assertContains(self.client.get(reverse("venues:recommend"), {"text": "zzzxqv"}), "No venues matched")

    def test_planner(self):
        today = timezone.localdate()
        rows = plan(today)
        self.assertTrue(rows)
        self.assertEqual([r["cycle"].submission_deadline for r in rows], sorted(r["cycle"].submission_deadline for r in rows))
        self.assertTrue(all(r["slack_days"] >= 0 for r in rows))
        far = plan(today + timedelta(days=60), domain="Security & Privacy")
        self.assertTrue(all(r["venue"].primary_domain == "Security & Privacy" for r in far))

    def test_plan_page(self):
        r = self.client.get(reverse("venues:plan"), {"ready": timezone.localdate().isoformat()})
        self.assertTrue(r.context["rows"])
        self.assertContains(r, "Slack")
        self.assertEqual(self.client.get(reverse("venues:plan"), {"ready": "garbage"}).status_code, 200)


class InsightsAndFeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def test_insights_api(self):
        d = self.client.get(reverse("venues:api_insights")).json()
        self.assertEqual(len(d["deadlines_by_month"]["labels"]), 12)
        self.assertEqual(sum(d["deadlines_by_month"]["values"]) <= d["totals"]["upcoming"], True)
        self.assertGreaterEqual(d["totals"]["venues"], 80)
        self.assertTrue(d["scatter"] and d["top_impact"][0][1] >= d["top_impact"][-1][1])
        self.assertEqual(sum(n for _, n in d["by_type"]), d["totals"]["venues"])

    def test_insights_page(self):
        r = self.client.get(reverse("venues:insights"))
        self.assertContains(r, "insights-data")
        self.assertContains(r, "chart.js@4.4.1")

    def test_suggest(self):
        r = self.client.get(reverse("venues:api_suggest"), {"q": "neurips"}).json()["results"]
        self.assertEqual(r[0]["acronym"], "NeurIPS")
        prefix = [x["acronym"] for x in self.client.get(reverse("venues:api_suggest"), {"q": "neur"}).json()["results"]]
        self.assertIn("NeurIPS", prefix[:3])
        self.assertEqual(self.client.get(reverse("venues:api_suggest")).json()["results"], [])
        self.assertLessEqual(len(self.client.get(reverse("venues:api_suggest"), {"q": "a"}).json()["results"]), 8)

    def test_filtered_calendar(self):
        r = self.client.get(reverse("venues:calendar_filtered"), {"core": "A*", "type": "Conference"})
        body = r.content.decode()
        self.assertEqual(r["Content-Type"], "text/calendar; charset=utf-8")
        self.assertGreater(body.count("BEGIN:VEVENT"), 10)
        self.assertNotIn("SUMMARY:Nature ", body)
        self.assertTrue(all(len(l.encode()) <= 75 for l in body.split("\r\n")))

    def test_atom_feed(self):
        r = self.client.get(reverse("venues:atom_feed"), {"status": "open"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/atom+xml", r["Content-Type"])
        self.assertIn("<entry>", r.content.decode())
        self.assertLessEqual(r.content.decode().count("<entry>"), 50)

    def test_api_docs(self):
        self.assertContains(self.client.get(reverse("venues:api_docs")), "/api/v1/me/targets/")

    def test_palette_and_nav_present(self):
        r = self.client.get(reverse("venues:list"))
        self.assertContains(r, "Command palette")
        for label in ("Recommend", "Planner", "Insights"):
            self.assertContains(r, label)


class TokenApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)
        cls.user = User.objects.create_user("alice", "a@example.com", "pw-12345-xyz")
        cls.hdr = {"HTTP_AUTHORIZATION": f"Bearer {cls.user.profile.api_token}"}

    def test_requires_token(self):
        for name in ("venues:api_me", "venues:api_me_targets", "venues:api_me_submissions"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 401, name)
        self.assertEqual(self.client.get(reverse("venues:api_me"), HTTP_AUTHORIZATION="Bearer nope").status_code, 401)
        self.assertEqual(self.client.get(reverse("venues:api_me"), HTTP_AUTHORIZATION=f"Token {self.user.profile.api_token}").status_code, 401)

    def test_me(self):
        d = self.client.get(reverse("venues:api_me"), **self.hdr).json()
        self.assertEqual(d["username"], "alice")

    def test_target_lifecycle(self):
        url = reverse("venues:api_me_targets")
        r = self.client.post(url, json.dumps({"slug": "cvpr"}), content_type="application/json", **self.hdr)
        self.assertEqual((r.status_code, r.json()["acronym"]), (201, "CVPR"))
        self.client.post(url, json.dumps({"slug": "cvpr"}), content_type="application/json", **self.hdr)  # idempotent
        self.assertEqual(self.client.get(url, **self.hdr).json()["count"], 1)
        self.assertEqual(VenueBookmark.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.client.delete(reverse("venues:api_me_target_delete", args=["cvpr"]), **self.hdr).status_code, 200)
        self.assertEqual(self.client.delete(reverse("venues:api_me_target_delete", args=["cvpr"]), **self.hdr).status_code, 404)
        self.assertEqual(self.client.get(url, **self.hdr).json()["count"], 0)

    def test_bad_requests(self):
        url = reverse("venues:api_me_targets")
        self.assertEqual(self.client.post(url, "not json", content_type="application/json", **self.hdr).status_code, 400)
        self.assertEqual(self.client.post(url, json.dumps({"slug": "nope"}), content_type="application/json", **self.hdr).status_code, 404)
        self.assertEqual(self.client.put(url, **self.hdr).status_code, 405)

    def test_token_user_isolation(self):
        bob = User.objects.create_user("bob", "b@example.com", "pw-12345-xyz")
        self.client.post(reverse("venues:api_me_targets"), json.dumps({"slug": "cvpr"}), content_type="application/json", **self.hdr)
        d = self.client.get(reverse("venues:api_me_targets"), HTTP_AUTHORIZATION=f"Bearer {bob.profile.api_token}").json()
        self.assertEqual(d["count"], 0)


class DetailPageExtrasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def test_related_venues(self):
        r = self.client.get(reverse("venues:detail", args=["cvpr"]))
        related = {v.acronym for v in r.context["related"]}
        self.assertTrue({"ICCV", "ECCV"} & related, related)
        self.assertNotIn("CVPR", related)

    def test_anonymous_sees_login_prompt_for_reviews(self):
        self.assertContains(self.client.get(reverse("venues:detail", args=["cvpr"])), "to share your experience")
