"""Purchase snapshot creation from authoritative package data."""

from copy import deepcopy

from django.db import transaction
from django.shortcuts import get_object_or_404

from offers_app.models import OfferDetail

from .models import Order

PACKAGE_FIELDS = [
    "title",
    "revisions",
    "delivery_time_in_days",
    "price",
    "features",
    "offer_type",
]


@transaction.atomic
def create_order(offer_detail_id, customer_user):
    """Copy the selected package and derive both participants server-side."""
    detail = get_object_or_404(
        OfferDetail.objects.select_for_update().select_related("offer"),
        pk=offer_detail_id,
    )
    snapshot = {
        field: deepcopy(getattr(detail, field)) for field in PACKAGE_FIELDS
    }
    return Order.objects.create(
        customer_user=customer_user,
        business_user=detail.offer.user,
        **snapshot,
    )
