from django.contrib import admin, messages

from .models import DeadlineChange, DeadlineSuggestion, VenueReview


@admin.register(DeadlineSuggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("cycle", "field", "new_value", "user", "status", "created_at")
    list_filter = ("status", "field")
    actions = ["approve", "reject"]

    @admin.action(description="Approve and apply selected suggestions")
    def approve(self, request, queryset):
        n = 0
        for s in queryset.filter(status="pending"):
            s.approve()
            n += 1
        self.message_user(request, f"Applied {n} suggestion(s).", messages.SUCCESS)

    @admin.action(description="Reject selected suggestions")
    def reject(self, request, queryset):
        queryset.filter(status="pending").update(status="rejected")


@admin.register(VenueReview)
class VenueReviewAdmin(admin.ModelAdmin):
    list_display = ("venue", "user", "rating", "outcome", "turnaround_days", "created_at")
    list_filter = ("outcome", "rating")


@admin.register(DeadlineChange)
class DeadlineChangeAdmin(admin.ModelAdmin):
    list_display = ("cycle", "field", "old_value", "new_value", "changed_at")
    readonly_fields = ("cycle", "field", "old_value", "new_value")
