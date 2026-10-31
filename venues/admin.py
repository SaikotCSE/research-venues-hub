import csv
from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Count, Min, Q
from django.http import HttpResponse
from django.utils import timezone

from .models import DeadlineCycle, ResearchSubfield, Venue, VenueBookmark
from .serializers import CSV_COLUMNS, venue_to_csv_row


class DeadlineCycleInline(admin.TabularInline):
    model = DeadlineCycle
    extra = 0
    ordering = ["-year"]
    fields = ("year", "timezone_label", "submission_open_date", "abstract_deadline", "submission_deadline", "notification_date",
              "camera_ready_date", "event_start_date", "event_end_date", "is_projected", "verified_at")
    readonly_fields = ("verified_at",)
    show_change_link = True


class DeadlineStatusFilter(admin.SimpleListFilter):
    title = "deadline status"
    parameter_name = "deadline"

    def lookups(self, request, model_admin):
        return [("upcoming", "Has upcoming deadline"), ("30d", "Closing within 30 days"), ("none", "No upcoming deadline"), ("projected", "Next deadline is projected")]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "upcoming":
            return queryset.filter(cycles__submission_deadline__gte=now).distinct()
        if self.value() == "30d":
            return queryset.filter(cycles__submission_deadline__gte=now, cycles__submission_deadline__lte=now + timedelta(days=30)).distinct()
        if self.value() == "none":
            return queryset.exclude(cycles__submission_deadline__gte=now)
        if self.value() == "projected":
            return queryset.filter(cycles__submission_deadline__gte=now, cycles__is_projected=True).distinct()
        return queryset


@admin.action(description="Export selected venues as CSV")
def export_selected_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="venues-selected.csv"'
    writer = csv.writer(response)
    writer.writerow(CSV_COLUMNS)
    for venue in queryset.prefetch_related("subfields", "cycles"):
        writer.writerow(venue_to_csv_row(venue))
    return response


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("acronym", "name", "venue_type", "primary_domain", "rank_display", "next_paper_deadline", "trackers", "country", "is_open_access")
    list_display_links = ("acronym", "name")
    list_filter = (DeadlineStatusFilter, "venue_type", "primary_domain", "core_rank", "ccf_rank", "quartile", "review_process", "is_open_access", "continent", "publisher", "is_rolling_submission")
    search_fields = ("name", "acronym", "description", "publisher", "subfields__name")
    search_help_text = "Search by name, acronym, description, publisher or subfield tag."
    prepopulated_fields = {"slug": ("acronym",)}
    filter_horizontal = ("subfields",)
    inlines = [DeadlineCycleInline]
    actions = [export_selected_csv]
    list_per_page = 50
    show_facets = admin.ShowFacets.ALWAYS
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Identity", {"fields": ("name", "acronym", "slug", "venue_type", "publisher")}),
        ("Description", {"fields": ("description", "scope", "primary_domain", "subfields")}),
        ("Conference ranks", {"fields": ("core_rank", "ccf_rank", "h5_index", "h5_median")}),
        ("Journal metrics", {"fields": ("impact_factor", "quartile", "citescore", "sjr", "issn")}),
        ("Timeline", {"fields": ("is_rolling_submission",)}),
        ("Location", {"fields": ("city", "country", "continent", "country_flag_emoji", "attendance_mode")}),
        ("Submission guidelines", {"fields": ("page_limit", "formatting_style", "template_url", "review_process", "is_open_access", "apc_cost_usd",
                                              "acceptance_rate", "official_website", "submission_portal_url")}),
        ("Record", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        now = timezone.now()
        return super().get_queryset(request).annotate(
            _next_deadline=Min("cycles__submission_deadline", filter=Q(cycles__submission_deadline__gte=now)),
            _trackers=Count("bookmarks", filter=Q(bookmarks__is_starred=True), distinct=True),
        )

    @admin.display(description="Rank")
    def rank_display(self, obj):
        return obj.rank_label

    @admin.display(description="Next paper deadline", ordering="_next_deadline")
    def next_paper_deadline(self, obj):
        return obj._next_deadline

    @admin.display(description="Trackers", ordering="_trackers")
    def trackers(self, obj):
        return obj._trackers


@admin.register(ResearchSubfield)
class ResearchSubfieldAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "venue_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_venues=Count("venues"))

    @admin.display(description="Venues", ordering="_venues")
    def venue_count(self, obj):
        return obj._venues


@admin.register(DeadlineCycle)
class DeadlineCycleAdmin(admin.ModelAdmin):
    list_display = ("venue", "year", "abstract_deadline", "submission_deadline", "notification_date", "event_start_date", "is_projected", "verified_at")
    list_filter = ("is_projected", "year", "timezone_label", "venue__venue_type")
    list_select_related = ("venue",)
    search_fields = ("venue__name", "venue__acronym")
    autocomplete_fields = ("venue",)
    date_hierarchy = "submission_deadline"
    actions = ["mark_verified", "mark_projected"]
    readonly_fields = ("verified_at",)
    show_facets = admin.ShowFacets.ALWAYS

    @admin.action(description="Mark dates as verified against the official call")
    def mark_verified(self, request, queryset):
        count = 0
        for cycle in queryset:
            cycle.mark_verified()
            count += 1
        self.message_user(request, f"Marked {count} cycle(s) as verified.", messages.SUCCESS)

    @admin.action(description="Mark dates as projected (unverified)")
    def mark_projected(self, request, queryset):
        updated = queryset.update(is_projected=True, verified_at=None)
        self.message_user(request, f"Marked {updated} cycle(s) as projected.", messages.WARNING)


@admin.register(VenueBookmark)
class VenueBookmarkAdmin(admin.ModelAdmin):
    list_display = ("venue", "user", "anon_key", "is_starred", "updated_at")
    list_filter = ("is_starred",)
    list_select_related = ("venue", "user")
    raw_id_fields = ("user",)
    autocomplete_fields = ("venue",)
    search_fields = ("venue__acronym", "user__username")
