"""Order response fields and narrowly scoped create/update inputs."""

from rest_framework import serializers

from orders_app.models import Order
from orders_app.services import create_order


class OrderSerializer(serializers.ModelSerializer):
    """Represent immutable purchased package data and order status."""

    price = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False, read_only=True
    )

    class Meta:
        """Declare the full documented order response."""

        model = Order
        fields = [
            "id",
            "customer_user",
            "business_user",
            "title",
            "revisions",
            "delivery_time_in_days",
            "price",
            "features",
            "offer_type",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OrderCreateSerializer(OrderSerializer):
    """Accept only a package identifier as purchase input."""

    offer_detail_id = serializers.IntegerField(write_only=True, min_value=1)

    class Meta(OrderSerializer.Meta):
        """Add the write-only source package ID to the response serializer."""

        fields = OrderSerializer.Meta.fields + ["offer_detail_id"]

    def create(self, validated_data):
        """Create the snapshot from the authoritative package."""
        return create_order(**validated_data)


class OrderStatusSerializer(OrderSerializer):
    """Permit only an explicit valid status value in a PATCH request."""

    status = serializers.ChoiceField(choices=Order.Status.choices)

    def validate(self, attrs):
        """Reject missing status and attempts to modify purchase data."""
        if set(self.initial_data) != {"status"}:
            raise serializers.ValidationError("Provide only the status field.")
        return attrs
