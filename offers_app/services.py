"""Atomic writes for offers with nested package data."""

from django.db import transaction

from .models import Offer, OfferDetail


@transaction.atomic
def create_offer(validated_data):
    """Create an offer and all validated tiers together."""
    details = validated_data.pop("details")
    offer = Offer.objects.create(**validated_data)
    for detail in details:
        detail.pop("id", None)
        OfferDetail.objects.create(offer=offer, **detail)
    return offer


def update_detail(offer, data):
    """Update one existing tier in place without changing its ID."""
    detail = offer.details.get(offer_type=data["offer_type"])
    for field, value in data.items():
        if field not in {"id", "offer_type"}:
            setattr(detail, field, value)
    detail.save()


@transaction.atomic
def update_offer(offer, validated_data):
    """Apply partial offer and tier changes as one transaction."""
    details = validated_data.pop("details", [])
    for field, value in validated_data.items():
        setattr(offer, field, value)
    offer.save()
    for detail in details:
        update_detail(offer, detail)
    return offer
