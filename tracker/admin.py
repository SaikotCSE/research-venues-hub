from django.contrib import admin

from .models import ChecklistItem, Paper, Submission


class ChecklistInline(admin.TabularInline):
    model = ChecklistItem
    extra = 0


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("paper", "venue", "user", "status", "updated_at")
    list_filter = ("status",)
    inlines = [ChecklistInline]


admin.site.register(Paper)
