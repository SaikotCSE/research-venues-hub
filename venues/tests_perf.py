"""Guard rails against N+1 query regressions on the hottest pages."""

from io import StringIO

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

HX = {"HTTP_HX_REQUEST": "true"}


class QueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)
        call_command("seed_demo", "--password", "demo-pass-123", stdout=StringIO())

    def count(self, url, params=None, **extra):
        cache.clear()
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url, params or {}, **extra)
        self.assertEqual(response.status_code, 200, url)
        return len(ctx.captured_queries)

    def test_explore_views_have_constant_query_counts(self):
        for view in ("grid", "table", "timeline", "calendar"):
            small = self.count(reverse("venues:list"), {"view": view, "page_size": 5}, **HX)
            self.assertLessEqual(small, 8, view)
        # 24 cards cost the same as a filtered page with 3 cards
        self.assertEqual(self.count(reverse("venues:list"), {}, **HX), self.count(reverse("venues:list"), {"q": "vision"}, **HX))

    def test_full_explore_page(self):
        self.assertLessEqual(self.count(reverse("venues:list")), 16)

    def test_detail_and_api(self):
        self.assertLessEqual(self.count(reverse("venues:detail", args=["cvpr"])), 12)
        self.assertLessEqual(self.count(reverse("venues:api_venues"), {"page_size": 100}), 6)
        self.assertLessEqual(self.count(reverse("venues:export_csv")), 5)

    def test_authenticated_pages(self):
        self.client.force_login(User.objects.get(username="demo"))
        self.assertLessEqual(self.count(reverse("accounts:dashboard")), 20)
        self.assertLessEqual(self.count(reverse("tracker:board")), 12)
        self.assertLessEqual(self.count(reverse("venues:targets")), 10)
        self.assertLessEqual(self.count(reverse("venues:detail", args=["cvpr"])), 20)
