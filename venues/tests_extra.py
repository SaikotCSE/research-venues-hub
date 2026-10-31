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
        self.assertContains(r, "venues/vendor/chart.umd.min.js")

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
        self.assertTrue(all(len(line.encode()) <= 75 for line in body.split("\r\n")))

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


class ExploreUXTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def get(self, **params):
        return self.client.get(reverse("venues:list"), params, HTTP_HX_REQUEST="true")

    def test_within_filter(self):
        from .filters import filter_venues

        now = timezone.now()
        for v in filter_venues(_QD({"within": "30"})):
            self.assertTrue(v.cycles.filter(submission_deadline__gte=now, submission_deadline__lte=now + timedelta(days=30)).exists(), v)
        self.assertEqual(filter_venues(_QD({"within": "bogus"})).count(), filter_venues(_QD({})).count())
        self.assertLessEqual(filter_venues(_QD({"within": "7"})).count(), filter_venues(_QD({"within": "90"})).count())

    def test_active_filter_chips(self):
        r = self.get(q="vision", core="A*", status="open", within="30", min_if="5", oa="1", tag="computer-vision")
        labels = [c["label"] for c in r.context["chips"]]
        for expected in ("“vision”", "CORE A*", "Open now", "Closing within 30 days", "IF ≥ 5", "Open access", "#Computer Vision"):
            self.assertIn(expected, labels)
        self.assertContains(r, "Remove filter: CORE A*")
        self.assertContains(r, "Clear all")

    def test_no_chips_without_filters(self):
        r = self.get()
        self.assertEqual(r.context["chips"], [])
        self.assertNotContains(r, "Clear all")

    def test_timeline_view(self):
        r = self.get(view="timeline", type="Conference")
        rows = list(r.context["page_obj"])
        self.assertTrue(rows)
        self.assertEqual(len(r.context["timeline"]["ticks"]), 12)
        for row in rows:
            for seg in row["segments"]:
                self.assertTrue(0 <= seg["left"] <= 100 and seg["width"] > 0, seg)
        keys = [row["sort_key"] for row in rows]
        self.assertEqual(keys, sorted(keys))
        self.assertContains(r, "Paper deadline")

    def test_timeline_hides_rolling_journals(self):
        r = self.get(view="timeline", type="Journal")
        self.assertGreater(r.context["rolling_hidden"], 0)
        self.assertContains(r, "rolling-submission journal")

    def test_table_has_sort_semantics(self):
        r = self.get(view="table", sort="impact_factor", dir="desc")
        self.assertContains(r, 'aria-sort="descending"')
        self.assertContains(r, "<caption")

    def test_full_page_has_hero_and_closing_soon(self):
        r = self.client.get(reverse("venues:list"))
        self.assertContains(r, "Closing soon")
        self.assertEqual(r.context["stats"]["venues"], 113)
        deadlines = [c.submission_deadline for c in r.context["closing_soon"]]
        self.assertEqual(deadlines, sorted(deadlines))
        self.assertTrue(all(d >= timezone.now() - timedelta(minutes=1) for d in deadlines))

    def test_tracker_counts_on_cards(self):
        from .models import Venue, VenueBookmark

        bob = User.objects.create_user("bob", "b@example.com", "pw-12345-xyz")
        VenueBookmark.objects.create(user=bob, venue=Venue.objects.get(slug="cvpr"))
        r = self.get(q="cvpr")
        self.assertContains(r, "1 tracking")

    def test_facets_are_cached_and_invalidated(self):
        from .filters import facet_options
        from .models import Venue

        before = facet_options()["countries"]
        Venue.objects.create(
            name="Atlantis Conf", acronym="ATL", slug="atl", venue_type="Conference", primary_domain="X", country="Atlantis", continent="Ocean"
        )
        self.assertIn("Atlantis", facet_options()["countries"])
        self.assertNotIn("Atlantis", before)

    def test_bookmark_toggle_sends_toast(self):
        r = self.client.post(reverse("venues:bookmark", args=["icml"]))
        self.assertEqual(json.loads(r["HX-Trigger"])["toast"]["message"], "Saved ICML to My Targets")


class _QD(dict):
    def getlist(self, key):
        v = self.get(key)
        return [] if v is None else (list(v) if isinstance(v, list | tuple) else [v])


class DetailSEOAndActionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def test_conference_jsonld_event(self):
        r = self.client.get(reverse("venues:detail", args=["cvpr"]))
        html = r.content.decode()
        block = html.split('<script type="application/ld+json">', 1)[1].split("</script>", 1)[0]
        data = json.loads(block)
        self.assertEqual(data["@type"], "Event")
        self.assertEqual(data["alternateName"], "CVPR")
        self.assertIn("startDate", data)
        self.assertEqual(data["location"]["address"]["addressCountry"], "USA")
        self.assertEqual(data["eventAttendanceMode"], "https://schema.org/OfflineEventAttendanceMode")

    def test_journal_jsonld_periodical(self):
        html = self.client.get(reverse("venues:detail", args=["nature"])).content.decode()
        data = json.loads(html.split('<script type="application/ld+json">', 1)[1].split("</script>", 1)[0])
        self.assertEqual(data["@type"], "Periodical")
        self.assertEqual(data["issn"], "0028-0836")

    def test_jsonld_is_escaped(self):
        from django.template import Context, Template

        out = Template("{% jsonld d %}").render(Context({"d": {"name": "</script><script>alert(1)</script>"}}))
        self.assertNotIn("</script><script>", out)
        self.assertIn("\\u003C/script\\u003E", out)

    def test_meta_and_breadcrumb(self):
        r = self.client.get(reverse("venues:detail", args=["cvpr"]))
        self.assertContains(r, '<meta property="og:type" content="article">')
        self.assertContains(r, 'aria-label="Breadcrumb"')
        self.assertContains(r, "CVPR 20")  # title contains the cycle year

    def test_calendar_links_and_stepper(self):
        r = self.client.get(reverse("venues:detail", args=["cvpr"]))
        links = r.context["calendar_links"]
        self.assertTrue(links["google"].startswith("https://calendar.google.com/calendar/render?"))
        self.assertIn("action=TEMPLATE", links["google"])
        self.assertTrue(links["outlook"].startswith("https://outlook.live.com/calendar/"))
        steps = r.context["steps"]
        self.assertEqual([s["label"] for s in steps][:2], ["Call opens", "Paper"])
        self.assertEqual(sum(1 for s in steps if s["state"] == "current"), 1)
        states = [s["state"] for s in steps]
        self.assertEqual(states, sorted(states, key=["done", "current", "upcoming"].index))
        self.assertContains(r, 'aria-current="step"')

    def test_rolling_journal_has_no_calendar_links(self):
        r = self.client.get(reverse("venues:detail", args=["nature"]))
        self.assertEqual(r.context["calendar_links"], {})
        self.assertContains(r, "Rolling submissions")
        self.assertNotContains(r, "Add to calendar")

    def test_tracking_count(self):
        from .models import Venue, VenueBookmark

        for name in ("u1", "u2"):
            VenueBookmark.objects.create(user=User.objects.create_user(name, f"{name}@x.com", "pw-12345-xyz"), venue=Venue.objects.get(slug="cvpr"))
        self.assertContains(self.client.get(reverse("venues:detail", args=["cvpr"])), "2 researchers tracking")

    def test_modal_quick_view(self):
        r = self.client.get(reverse("venues:modal", args=["cvpr"]))
        self.assertContains(r, "Open full page")
        self.assertNotContains(r, "<html")


class SnippetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def test_latex_preambles_match_official_classes(self):
        from .models import Venue

        expected = {
            "cvpr": "{cvpr}",
            "icml": "icml2025",
            "iclr": "iclr2025_conference",
            "acl": "[review]{acl}",
            "aaai": "aaai25",
            "osdi": "usenix",
            "kdd": "acmart",
            "miccai": "llncs",
            "media": "elsarticle",
            "nature": "sn-jnl",
            "ieee-tmi": "[journal]{IEEEtran}",
        }
        for slug, needle in expected.items():
            self.assertIn(needle, Venue.objects.get(slug=slug).latex_snippet, slug)

    def test_double_blind_acm_uses_anonymous_review_mode(self):
        from .models import Venue

        self.assertIn("anonymous", Venue.objects.get(slug="kdd").latex_snippet)
        chi = Venue.objects.get(slug="chi")  # single-blind ACM venue
        self.assertIn("{acmart}", chi.latex_snippet)
        self.assertNotIn("anonymous]", chi.latex_snippet)

    def test_bibtex_year_follows_next_cycle(self):
        from .models import Venue

        v = Venue.objects.get(slug="cvpr")
        self.assertIn(f"cvpr{v.next_cycle.year}", v.bibtex)


class CompareTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def rows(self, *slugs):
        r = self.client.get(reverse("venues:compare"), {"s": list(slugs)})
        return r, {row["key"]: row for row in r.context["rows"]}

    def test_best_values_are_flagged(self):
        r, rows = self.rows("cvpr", "iccv", "eccv")
        self.assertEqual([c["best"] for c in rows["h5_index"]["cells"]], [True, False, False])  # CVPR has the highest h5
        self.assertEqual([c["best"] for c in rows["acceptance_rate"]["cells"]], [True, False, False])  # lowest rate = most selective
        self.assertEqual(sum(c["best"] for c in rows["next_deadline"]["cells"]), 1)
        self.assertFalse(any(c["best"] for c in rows["type"]["cells"]))
        self.assertContains(r, "(best)")

    def test_ties_and_missing_values_are_not_flagged(self):
        _, rows = self.rows("cvpr", "nature")
        self.assertFalse(any(c["best"] for c in rows["impact_factor"]["cells"]), "only one venue has an IF")

    def test_remove_links_on_full_page(self):
        r, _ = self.rows("cvpr", "iccv")
        self.assertEqual(r.context["remove_links"]["cvpr"], "?s=iccv")
        self.assertContains(r, 'aria-label="Remove CVPR from comparison"')

    def test_drawer_variant_uses_alpine_remove(self):
        r = self.client.get(reverse("venues:compare"), {"s": ["cvpr", "iccv"]}, HTTP_HX_REQUEST="true")
        self.assertContains(r, "$store.compare.toggle('cvpr'")
