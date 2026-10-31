from django.contrib import admin

from .models import DeadlineCycle, ResearchSubfield, Venue, VenueBookmark


class DeadlineCycleInline(admin.TabularInline):
    model = DeadlineCycle
    extra = 0
    ordering = ["-year"]


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("acronym", "name", "venue_type", "primary_domain", "core_rank", "ccf_rank", "quartile", "impact_factor", "country", "is_open_access")
    list_filter = ("venue_type", "primary_domain", "core_rank", "ccf_rank", "quartile", "review_process", "is_open_access", "continent", "publisher", "is_rolling_submission")
    search_fields = ("name", "acronym", "description", "publisher", "subfields__name")
    prepopulated_fields = {"slug": ("acronym",)}
    filter_horizontal = ("subfields",)
    inlines = [DeadlineCycleInline]
    fieldsets = (
        ("Identity", {"fields": ("name", "acronym", "slug", "venue_type", "publisher")}),
        ("Description", {"fields": ("description", "scope", "primary_domain", "subfields")}),
        ("Conference ranks", {"fields": ("core_rank", "ccf_rank", "h5_index", "h5_median")}),
        ("Journal metrics", {"fields": ("impact_factor", "quartile", "citescore", "sjr", "issn")}),
        ("Timeline", {"fields": ("is_rolling_submission",)}),
        ("Location", {"fields": ("city", "country", "continent", "country_flag_emoji", "attendance_mode")}),
        ("Submission guidelines", {"fields": ("page_limit", "formatting_style", "template_url", "review_process", "is_open_access", "apc_cost_usd", "acceptance_rate", "official_website", "submission_portal_url")}),
    )


@admin.register(ResearchSubfield)
class ResearchSubfieldAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(DeadlineCycle)
class DeadlineCycleAdmin(admin.ModelAdmin):
    list_display = ("venue", "year", "abstract_deadline", "submission_deadline", "notification_date", "event_start_date")
    list_filter = ("year", "timezone_label")
    search_fields = ("venue__name", "venue__acronym")
    date_hierarchy = "submission_deadline"


@admin.register(VenueBookmark)
class VenueBookmarkAdmin(admin.ModelAdmin):
    list_display = ("venue", "session_key", "is_starred", "updated_at")
    list_filter = ("is_starred",)
