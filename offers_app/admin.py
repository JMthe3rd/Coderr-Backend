"""Manage offers and their packages in Django admin."""

from django.contrib import admin

from .models import Offer, OfferDetail


class OfferDetailInline(admin.TabularInline):
    """Edit package tiers within their parent offer."""

    model = OfferDetail
    extra = 0
    max_num = 3


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    """Search and inspect marketplace offers."""

    list_display = ["title", "user", "updated_at"]
    search_fields = ["title", "user__username"]
    inlines = [OfferDetailInline]


@admin.register(OfferDetail)
class OfferDetailAdmin(admin.ModelAdmin):
    """Inspect purchasable tiers directly."""

    list_display = ["title", "offer", "offer_type", "price"]
    list_filter = ["offer_type"]
