"""Manage marketplace profiles through Django admin."""

from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Expose searchable profiles and role filters."""

    list_display = ["user", "type", "location", "created_at"]
    list_filter = ["type"]
    search_fields = ["user__username", "user__email"]
