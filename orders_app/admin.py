"""Inspect purchased snapshots and manage order status in Django admin."""

from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Make purchase data read-only while allowing staff to manage status."""

    list_display = ["id", "title", "customer_user", "business_user", "status"]
    list_filter = ["status", "offer_type"]
    search_fields = [
        "title",
        "customer_user__username",
        "business_user__username",
    ]
    readonly_fields = [
        "customer_user",
        "business_user",
        "title",
        "revisions",
        "delivery_time_in_days",
        "price",
        "features",
        "offer_type",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        """Require order creation through the validated purchase API."""
        return False
