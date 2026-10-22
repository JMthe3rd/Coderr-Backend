"""Offer package validation and method-specific response contracts."""

import json

from django.contrib.auth import get_user_model
from rest_framework import serializers

from offers_app.models import Offer, OfferDetail
from offers_app.services import create_offer, update_offer


class OfferDetailSerializer(serializers.ModelSerializer):
    """Validate and represent purchasable package data."""

    id = serializers.IntegerField(required=False)
    price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, coerce_to_string=False
    )
    features = serializers.ListField(child=serializers.CharField())

    class Meta:
        """Declare fields without exposing the parent offer reference."""

        model = OfferDetail
        fields = [
            "id",
            "title",
            "revisions",
            "delivery_time_in_days",
            "price",
            "features",
            "offer_type",
        ]


class OfferWriteSerializer(serializers.ModelSerializer):
    """Validate nested writes while retaining IDs of existing packages."""

    details = OfferDetailSerializer(many=True)

    class Meta:
        """Return offer content with the complete package data after saving."""

        model = Offer
        fields = ["id", "title", "image", "description", "details"]
        read_only_fields = ["id"]

    def to_internal_value(self, data):
        """Accept nested JSON packages alongside multipart image uploads."""
        if hasattr(data, "get") and isinstance(data.get("details"), str):
            data = data.dict() if hasattr(data, "dict") else data.copy()
            try:
                data["details"] = json.loads(data["details"])
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    {"details": "Provide a valid JSON list."}
                )
        return super().to_internal_value(data)

    def validate_image(self, value):
        """Accept common raster images of at most five megabytes."""
        if value is None:
            return value
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Maximum image size is 5 MB.")
        if value.image.format not in {"JPEG", "PNG", "WEBP"}:
            raise serializers.ValidationError("Use a JPEG, PNG or WebP image.")
        return value

    def validate_details(self, value):
        """Require all three unique tiers on creation and typed PATCH data."""
        tiers = [item.get("offer_type") for item in value]
        if None in tiers or len(tiers) != len(set(tiers)):
            raise serializers.ValidationError("Provide each offer_type once.")
        if self.instance is None and set(tiers) != set(
            OfferDetail.Type.values
        ):
            raise serializers.ValidationError(
                "Provide basic, standard and premium."
            )
        if self.instance is not None:
            self.validate_detail_ids(value)
        return value

    def validate_detail_ids(self, details):
        """Reject IDs that do not belong to the specified offer and tier."""
        existing = dict(self.instance.details.values_list("offer_type", "id"))
        for detail in details:
            if "id" in detail and detail["id"] != existing.get(
                detail["offer_type"]
            ):
                raise serializers.ValidationError(
                    "Package ID does not match its tier."
                )

    def create(self, validated_data):
        """Create the offer with its three packages atomically."""
        return create_offer(validated_data)

    def update(self, instance, validated_data):
        """Persist nested partial updates atomically."""
        return update_offer(instance, validated_data)


class OfferDetailLinkSerializer(serializers.ModelSerializer):
    """Link read responses to the separate package endpoint."""

    url = serializers.SerializerMethodField()

    class Meta:
        """Expose only the ID and URL in offer read responses."""

        model = OfferDetail
        fields = ["id", "url"]

    def get_url(self, obj):
        """Match relative list links and absolute offer detail links."""
        if self.context["view"].action == "list":
            return f"/offerdetails/{obj.pk}/"
        return self.context["request"].build_absolute_uri(
            f"/api/offerdetails/{obj.pk}/"
        )


class OfferReadSerializer(serializers.ModelSerializer):
    """Represent read-only offer metadata and aggregate package minima."""

    details = OfferDetailLinkSerializer(many=True, read_only=True)
    min_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False, read_only=True
    )
    min_delivery_time = serializers.IntegerField(read_only=True)

    class Meta:
        """Declare the authenticated detail response fields."""

        model = Offer
        fields = [
            "id",
            "user",
            "title",
            "image",
            "description",
            "created_at",
            "updated_at",
            "details",
            "min_price",
            "min_delivery_time",
        ]


class OfferUserSerializer(serializers.ModelSerializer):
    """Expose only the public creator summary."""

    class Meta:
        """Avoid returning email or other private account fields."""

        model = get_user_model()
        fields = ["first_name", "last_name", "username"]


class OfferListSerializer(OfferReadSerializer):
    """Add the creator summary required by the public offer list."""

    user_details = OfferUserSerializer(source="user", read_only=True)

    class Meta(OfferReadSerializer.Meta):
        """Append creator details to the read response."""

        fields = OfferReadSerializer.Meta.fields + ["user_details"]
