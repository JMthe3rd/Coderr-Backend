"""Search and inspect customer reviews in Django admin."""

from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Expose ratings with author and business account context."""

    list_display = ["id", "business_user", "reviewer", "rating", "updated_at"]
    list_filter = ["rating"]
    search_fields = [
        "description",
        "business_user__username",
        "reviewer__username",
    ]
    readonly_fields = ["created_at", "updated_at"]
