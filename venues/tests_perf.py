"""Guard rails against N+1 query regressions on the hottest endpoints."""

from io import StringIO

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

APP = "/api/app"


class QueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_venues", verbosity=0)
        call_command("seed_demo", "--password", "demo-pass-123", stdout=StringIO())

    def count(self, url, params=None):
        cache.clear()
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url, params or {})
        self.assertEqual(response.status_code, 200, url)
        return len(ctx.captured_queries)

    def test_explore_endpoints_have_constant_query_counts(self):
        for path in ("/explore/", "/explore/timeline/", "/explore/calendar/"):
            full = self.count(APP + path)
            self.assertLessEqual(full, 6, path)
            # 24 cards cost the same as a filtered page with 3 cards
            self.assertEqual(full, self.count(APP + path, {"q": "vision"}), path)

    def test_server_rendered_shells(self):
        self.assertLessEqual(self.count(reverse("venues:list")), 15)  # session + facets + home + first explore page
        self.assertLessEqual(self.count(reverse("venues:detail", args=["cvpr"])), 13)

    def test_detail_and_public_api(self):
        self.assertLessEqual(self.count(f"{APP}/venues/cvpr/"), 13)
        self.assertLessEqual(self.count(f"{APP}/compare/", {"s": ["cvpr", "iccv", "nature", "kdd"]}), 4)
        self.assertLessEqual(self.count(reverse("venues:api_venues"), {"page_size": 100}), 6)
        self.assertLessEqual(self.count(reverse("venues:export_csv")), 5)

    def test_authenticated_endpoints(self):
        self.client.force_login(User.objects.get(username="demo"))
        self.assertLessEqual(self.count(f"{APP}/me/dashboard/"), 18)
        self.assertLessEqual(self.count(f"{APP}/tracker/board/"), 5)
        self.assertLessEqual(self.count(f"{APP}/targets/"), 7)
        self.assertLessEqual(self.count(f"{APP}/venues/cvpr/"), 19)
        self.assertLessEqual(self.count(f"{APP}/me/notifications/"), 6)
