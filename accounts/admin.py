from django.contrib import admin

from .models import Notification, SavedSearch, UserProfile, VenueList

admin.site.register(UserProfile)
admin.site.register(SavedSearch)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "message", "created_at", "read_at")
    list_filter = ("kind",)


@admin.register(VenueList)
class VenueListAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_public")
    filter_horizontal = ("venues",)
