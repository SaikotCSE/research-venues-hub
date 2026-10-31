from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from accounts.models import VenueList
from venues.models import Venue


class StaticViewSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return ["venues:list", "venues:recommend", "venues:plan", "venues:insights", "venues:api_docs", "community:changes"]

    def location(self, item):
        return reverse(item)


class VenueSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Venue.objects.order_by("slug").only("slug", "updated_at")

    def lastmod(self, venue):
        return venue.updated_at


class PublicListSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.4

    def items(self):
        return VenueList.objects.filter(is_public=True).order_by("slug")

    def location(self, obj):
        return reverse("accounts:list_detail", args=[obj.slug])


SITEMAPS = {"static": StaticViewSitemap, "venues": VenueSitemap, "lists": PublicListSitemap}
