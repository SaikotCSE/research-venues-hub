import csv
import io
import json
from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .filters import filter_venues
from .models import DeadlineCycle, ResearchSubfield, Venue, VenueBookmark
from .seed_data import ALL_VENUES

HX = {"HTTP_HX_REQUEST": "true"}


def make_venue(acronym="TST", **kw):
    defaults = dict(name=f"Test {acronym}", acronym=acronym, slug=acronym.lower(), venue_type="Conference",
                    primary_domain="AI / Machine Learning")
    defaults.update(kw)
    return Venue.objects.create(**defaults)


def make_cycle(venue, days_to_deadline, year=2030, open_days_before=60, **kw):
    now = timezone.now()
    deadline = now + timedelta(days=days_to_deadline)
    return DeadlineCycle.objects.create(
        venue=venue, year=year, submission_deadline=deadline,
        submission_open_date=deadline - timedelta(days=open_days_before),
        event_start_date=(deadline + timedelta(days=120)).date(), **kw)


class ModelTests(TestCase):
    def test_slug_and_str(self):
        tag = ResearchSubfield.objects.create(name="Computer Vision")
        self.assertEqual(tag.slug, "computer-vision")
        self.assertEqual(str(make_venue("ABC")), "ABC")

    def test_unique_cycle_per_year(self):
        v = make_venue()
        make_cycle(v, 10, year=2030)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_cycle(v, 20, year=2030)

    def test_status_open_upcoming_past_rolling(self):
        open_v = make_venue("OPEN"); make_cycle(open_v, 10, open_days_before=30)
        up_v = make_venue("UP"); make_cycle(up_v, 100, open_days_before=30)
        past_v = make_venue("PAST"); make_cycle(past_v, -5, year=2024)
        roll_v = make_venue("ROLL", venue_type="Journal", is_rolling_submission=True)
        statuses = {v.acronym: v.deadline_status for v in Venue.objects.prefetch_related("cycles")}
        self.assertEqual(statuses, {"OPEN": "open", "UP": "upcoming", "PAST": "past", "ROLL": "rolling"})
        self.assertIsNone(roll_v.next_deadline)

    def test_next_deadline_prefers_abstract(self):
        v = make_venue()
        c = make_cycle(v, 30)
        c.abstract_deadline = timezone.now() + timedelta(days=5)
        c.save()
        label, when = Venue.objects.get(pk=v.pk).next_deadline
        self.assertEqual(label, "Abstract")
        self.assertEqual(when, c.abstract_deadline)

    def test_aoe_property(self):
        v = make_venue(); c = make_cycle(v, 10)
        self.assertEqual(c.submission_aoe, c.submission_deadline - timedelta(hours=12))

    def test_snippets(self):
        v = make_venue(formatting_style="ACM sigconf", review_process="Double-Blind", issn="1234-5678", publisher="ACM")
        self.assertIn("acmart", v.latex_snippet)
        self.assertIn("@inproceedings", v.bibtex)
        j = make_venue("JRN", venue_type="Journal", formatting_style="IEEEtran")
        self.assertIn("@article", j.bibtex)
        self.assertIn("journal", j.latex_snippet)

    def test_rank_label(self):
        self.assertEqual(make_venue("R1", core_rank="A*", ccf_rank="A").rank_label, "CORE A* · CCF A")
        self.assertEqual(make_venue("R2", venue_type="Journal", quartile="Q1").rank_label, "Q1")
        self.assertEqual(make_venue("R3").rank_label, "Unranked")


class SeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def test_seed_count_at_least_80(self):
        self.assertGreaterEqual(Venue.objects.count(), 80)
        self.assertEqual(Venue.objects.count(), len(ALL_VENUES))

    def test_required_venues_present(self):
        required = ["NeurIPS", "ICML", "ICLR", "CVPR", "ICCV", "ECCV", "AAAI", "IJCAI", "ACL", "EMNLP", "NAACL", "KDD",
                    "MICCAI", "ISBI", "IEEE TMI", "MedIA", "Bioinformatics", "Nature Medicine", "Lancet Digital Health",
                    "OSDI", "SOSP", "SIGCOMM", "IEEE S&P", "USENIX Security", "CCS", "NDSS",
                    "ICSE", "FSE", "ASE", "WWW", "SIGIR", "CHI",
                    "Nature", "Science", "PNAS", "IEEE TPAMI", "JMLR", "Nature Communications"]
        have = set(Venue.objects.values_list("acronym", flat=True))
        self.assertEqual([r for r in required if r not in have], [])

    def test_all_venue_types_and_data_quality(self):
        types = set(Venue.objects.values_list("venue_type", flat=True))
        self.assertEqual(types, {"Conference", "Journal", "Workshop/Symposium"})
        for v in Venue.objects.prefetch_related("cycles", "subfields"):
            self.assertTrue(v.description and v.official_website.startswith("https://"), v.acronym)
            self.assertTrue(v.country_flag_emoji and v.continent, v.acronym)
            self.assertGreaterEqual(v.subfields.count(), 1, v.acronym)
            if v.is_journal:
                self.assertTrue(v.is_rolling_submission and v.issn, v.acronym)
            else:
                self.assertTrue(v.cycles.exists(), v.acronym)

    def test_cycles_are_chronological(self):
        for c in DeadlineCycle.objects.select_related("venue"):
            seq = [d for d in (c.abstract_deadline, c.submission_deadline, c.notification_date, c.camera_ready_date) if d]
            self.assertEqual(seq, sorted(seq), str(c))
            if c.camera_ready_date:
                self.assertLessEqual(c.camera_ready_date.date(), c.event_start_date, str(c))

    def test_idempotent(self):
        before = (Venue.objects.count(), DeadlineCycle.objects.count(), ResearchSubfield.objects.count())
        call_command("seed_venues", verbosity=0)
        self.assertEqual(before, (Venue.objects.count(), DeadlineCycle.objects.count(), ResearchSubfield.objects.count()))

    def test_aoe_timezone_conversion(self):
        c = DeadlineCycle.objects.filter(timezone_label="AoE", venue__acronym="NeurIPS").first()
        # 23:59 AoE == 11:59 UTC the next day
        self.assertEqual((c.submission_deadline.hour, c.submission_deadline.minute), (11, 59))

    def test_status_mix_exists(self):
        statuses = {v.deadline_status for v in Venue.objects.prefetch_related("cycles")}
        self.assertEqual(statuses, {"open", "upcoming", "rolling", "past"})


class ViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)

    def acronyms(self, **params):
        return {v.acronym for v in filter_venues(_QD(params))}

    # ---- list / filters
    def test_list_page_renders(self):
        r = self.client.get(reverse("venues:list"))
        self.assertContains(r, "VenuePulse")
        self.assertContains(r, 'id="filters"')
        self.assertEqual(r.context["total"], Venue.objects.count())
        self.assertContains(self.client.get(reverse("venues:list"), {"q": "neurips"}), "NeurIPS")

    def test_htmx_returns_partial(self):
        r = self.client.get(reverse("venues:list"), **HX)
        self.assertNotContains(r, "<html")
        self.assertContains(r, "showing 1–24")

    def test_view_modes(self):
        for mode, marker in (("grid", "<article"), ("table", "<table"), ("calendar", "No milestones")):
            r = self.client.get(reverse("venues:list"), {"view": mode}, **HX)
            self.assertEqual(r.status_code, 200)
            if mode == "calendar":
                self.assertContains(r, "next 12 months")
            else:
                self.assertContains(r, marker)

    def test_filter_venue_type(self):
        r = self.client.get(reverse("venues:api_venues"), {"type": "Journal", "page_size": 200}).json()
        self.assertTrue(r["count"] > 20)
        self.assertTrue(all(v["venue_type"] == "Journal" for v in r["results"]))

    def test_filter_core_and_ccf(self):
        self.assertTrue({"NeurIPS", "CVPR"} <= self.acronyms(core="A*"))
        self.assertNotIn("WACV", self.acronyms(core="A*"))
        self.assertIn("WACV", self.acronyms(core=["A*", "A"]))
        self.assertTrue(all(Venue.objects.get(acronym=a).ccf_rank == "A" for a in self.acronyms(ccf="A")))

    def test_filter_quartile_and_impact_factor(self):
        self.assertIn("Nature", self.acronyms(quartile="Q1"))
        high = self.acronyms(min_if="40")
        self.assertEqual(high, {"Nature", "Science", "Nature Medicine"})
        self.assertEqual(self.acronyms(min_if="not-a-number"), self.acronyms())

    def test_filter_domain_tag_country_continent_review_oa(self):
        self.assertIn("MICCAI", self.acronyms(domain="Medical Imaging & Bioinformatics"))
        self.assertIn("CVPR", self.acronyms(tag="3d-vision"))
        self.assertIn("ACL", self.acronyms(country="Austria"))
        self.assertTrue(all(Venue.objects.get(acronym=a).continent == "Europe" for a in self.acronyms(continent="Europe")))
        self.assertTrue(all(Venue.objects.get(acronym=a).review_process == "Open Peer Review" for a in self.acronyms(review="Open Peer Review")))
        self.assertIn("JMLR", self.acronyms(oa="1"))
        self.assertNotIn("Nature", self.acronyms(oa="1"))

    def test_filter_status(self):
        self.assertTrue(self.acronyms(status="rolling") >= {"Nature", "JMLR"})
        self.assertNotIn("CVPR", self.acronyms(status="rolling"))
        for status in ("open", "upcoming", "past"):
            got = self.acronyms(status=status)
            self.assertTrue(got, status)
            actual = {v.acronym: v.deadline_status for v in Venue.objects.prefetch_related("cycles") if v.acronym in got}
            self.assertEqual(set(actual.values()), {status})

    def test_search(self):
        self.assertIn("MICCAI", self.acronyms(q="medical image computing"))
        self.assertIn("NeurIPS", self.acronyms(q="neurips"))
        self.assertEqual(self.acronyms(q="zzzz-no-such-venue"), set())

    def test_sorting(self):
        by_if = list(filter_venues(_QD({"sort": "impact_factor", "dir": "desc"})).values_list("impact_factor", flat=True))
        non_null = [x for x in by_if if x is not None]
        self.assertEqual(non_null, sorted(non_null, reverse=True))
        self.assertTrue(all(x is None for x in by_if[len(non_null):]), "nulls last")
        dl = [v.next_dl for v in filter_venues(_QD({"sort": "deadline"})) if v.next_dl]
        self.assertEqual(dl, sorted(dl))
        rank = [v.rank_score for v in filter_venues(_QD({"sort": "rank"}))]
        self.assertEqual(rank, sorted(rank, reverse=True))
        self.assertTrue(filter_venues(_QD({"sort": "bogus"})).exists())

    def test_pagination(self):
        r = self.client.get(reverse("venues:list"), {"page": 2}, **HX)
        self.assertContains(r, "Page <strong")
        self.assertEqual(r.context["page_obj"].number, 2)

    # ---- detail / modal / ics
    def test_detail_page(self):
        r = self.client.get(reverse("venues:detail", args=["cvpr"]))
        self.assertContains(r, "Submission &amp; formatting guide")
        self.assertContains(r, "Copy LaTeX / BibTeX info")
        self.assertContains(r, "@inproceedings")
        self.assertContains(r, reverse("venues:ics", args=["cvpr"]))
        self.assertEqual(self.client.get("/venue/does-not-exist/").status_code, 404)

    def test_detail_journal(self):
        r = self.client.get(reverse("venues:detail", args=["nature"]))
        self.assertContains(r, "Rolling submissions")
        self.assertContains(r, "@article")

    def test_modal(self):
        r = self.client.get(reverse("venues:modal", args=["icml"]))
        self.assertContains(r, "ICML")
        self.assertNotContains(r, "<html")

    def test_ics(self):
        r = self.client.get(reverse("venues:ics", args=["cvpr"]))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r["Content-Type"].startswith("text/calendar"))
        self.assertIn("cvpr-deadlines.ics", r["Content-Disposition"])
        body = r.content.decode()
        self.assertTrue(body.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(body.endswith("END:VCALENDAR\r\n"))
        self.assertEqual(body.count("BEGIN:VEVENT"), body.count("END:VEVENT"))
        self.assertIn("SUMMARY:CVPR", body)
        self.assertIn("DTSTART:", body)
        self.assertTrue(all(len(line.encode()) <= 75 for line in body.split("\r\n")))

    def test_ics_404_for_rolling_journal(self):
        self.assertEqual(self.client.get(reverse("venues:ics", args=["nature"])).status_code, 404)

    # ---- compare
    def test_compare(self):
        r = self.client.get(reverse("venues:compare"), {"s": ["cvpr", "nature", "cvpr"]})
        self.assertContains(r, "CVPR")
        self.assertContains(r, "Nature")
        self.assertEqual(len(r.context["venues"]), 2)

    def test_compare_limited_to_four(self):
        r = self.client.get(reverse("venues:compare"), {"s": ["cvpr", "icml", "iclr", "kdd", "nature"]}, **HX)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode().count("hover:text-brand-600"), 4)

    def test_compare_empty(self):
        self.assertContains(self.client.get(reverse("venues:compare"), **HX), "Tick")

    # ---- bookmarks & notes
    def test_bookmark_toggle_and_targets(self):
        url = reverse("venues:bookmark", args=["cvpr"])
        self.assertEqual(self.client.get(url).status_code, 405)
        r = self.client.post(url)
        self.assertContains(r, 'aria-pressed="true"')
        trigger = json.loads(r["HX-Trigger"])
        self.assertTrue(trigger["targets-changed"])
        self.assertIn("Saved CVPR", trigger["toast"]["message"])
        self.assertContains(self.client.get(reverse("venues:targets")), "CVPR")
        self.assertContains(self.client.post(url), 'aria-pressed="false"')
        self.assertNotContains(self.client.get(reverse("venues:targets")), "article")

    def test_bookmarks_are_per_session(self):
        self.client.post(reverse("venues:bookmark", args=["cvpr"]))
        from django.test import Client
        other = Client()
        self.assertNotContains(other.get(reverse("venues:targets")), "CVPR")

    def test_notes(self):
        self.client.post(reverse("venues:note", args=["kdd"]), {"note": "Submit with Alice"})
        bm = VenueBookmark.objects.get(venue__slug="kdd")
        self.assertEqual(bm.note, "Submit with Alice")
        self.assertFalse(bm.is_starred)
        self.assertContains(self.client.get(reverse("venues:detail", args=["kdd"])), "Submit with Alice")

    def test_starred_state_in_list(self):
        self.client.post(reverse("venues:bookmark", args=["cvpr"]))
        r = self.client.get(reverse("venues:list"), {"q": "cvpr"}, **HX)
        self.assertContains(r, 'aria-pressed="true"')

    # ---- export
    def test_export_csv(self):
        r = self.client.get(reverse("venues:export_csv"))
        self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        rows = list(csv.DictReader(io.StringIO(r.content.decode())))
        self.assertEqual(len(rows), Venue.objects.count())
        self.assertIn("acronym", rows[0])
        self.assertIn("NeurIPS", {row["acronym"] for row in rows})

    def test_export_csv_respects_filters_and_scope(self):
        r = self.client.get(reverse("venues:export_csv"), {"type": "Journal"})
        rows = list(csv.DictReader(io.StringIO(r.content.decode())))
        self.assertTrue(rows and all(row["venue_type"] == "Journal" for row in rows))
        self.client.post(reverse("venues:bookmark", args=["icml"]))
        r = self.client.get(reverse("venues:export_csv"), {"scope": "targets"})
        rows = list(csv.DictReader(io.StringIO(r.content.decode())))
        self.assertEqual([row["acronym"] for row in rows], ["ICML"])

    def test_csv_formula_injection_guard(self):
        make_venue("EVIL", name="=HYPERLINK(\"http://x\")", slug="evil")
        r = self.client.get(reverse("venues:export_csv"), {"q": "EVIL"})
        self.assertIn("'=HYPERLINK", r.content.decode())

    def test_export_json(self):
        r = self.client.get(reverse("venues:export_json"), {"q": "neurips"})
        data = json.loads(r.content)
        self.assertEqual(data["count"], len(data["results"]))
        neurips = next(v for v in data["results"] if v["acronym"] == "NeurIPS")
        self.assertTrue(neurips["cycles"])

    # ---- API
    def test_api(self):
        data = self.client.get(reverse("venues:api_venues"), {"page_size": 10}).json()
        self.assertEqual(len(data["results"]), 10)
        self.assertEqual(data["count"], Venue.objects.count())
        detail = self.client.get(reverse("venues:api_venue_detail", args=["miccai"])).json()
        self.assertEqual(detail["core_rank"], "A")
        self.assertIn("cycles", detail)
        self.assertTrue(self.client.get(reverse("venues:api_tags")).json()["results"])
        stats = self.client.get(reverse("venues:api_stats")).json()
        self.assertGreaterEqual(stats["venues"], 80)
        self.assertEqual(self.client.get("/api/venues/nope/").status_code, 404)
        self.assertEqual(self.client.get(reverse("venues:api_venues"), {"page_size": "abc"}).status_code, 200)

    def test_json_numbers_are_numeric(self):
        d = self.client.get(reverse("venues:api_venue_detail", args=["nature"])).json()
        self.assertIsInstance(d["impact_factor"], float)
        self.assertEqual(d["next_deadline"], None)
        self.assertEqual(d["deadline_status"], "rolling")

    def test_admin_registered(self):
        from django.contrib import admin
        for m in (Venue, DeadlineCycle, ResearchSubfield, VenueBookmark):
            self.assertIn(m, admin.site._registry)

    def test_decimal_fields(self):
        v = Venue.objects.get(acronym="Nature")
        self.assertIsInstance(v.impact_factor, Decimal)


class _QD(dict):
    """Tiny QueryDict stand-in so filters can be exercised with plain dicts."""

    def getlist(self, key):
        v = self.get(key)
        if v is None:
            return []
        return list(v) if isinstance(v, (list, tuple)) else [v]
