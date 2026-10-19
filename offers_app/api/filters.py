"""Validate offer query parameters before applying filters."""

from rest_framework import serializers
from rest_framework.filters import BaseFilterBackend


class OfferQuerySerializer(serializers.Serializer):
    """Validate supported numeric filters and pagination size."""

    creator_id = serializers.IntegerField(required=False, min_value=1)
    min_price = serializers.DecimalField(
        required=False, max_digits=12, decimal_places=2, min_value=0
    )
    max_delivery_time = serializers.IntegerField(required=False, min_value=1)
    page_size = serializers.IntegerField(
        required=False, min_value=1, max_value=100
    )


class OfferFilterBackend(BaseFilterBackend):
    """Filter against aggregate minimum price and delivery time."""

    filter_mapping = {
        "creator_id": "user_id",
        "min_price": "min_price__gte",
        "max_delivery_time": "min_delivery_time__lte",
    }

    def filter_queryset(self, request, queryset, view):
        """Reject malformed query values and apply validated filters."""
        serializer = OfferQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = {
            lookup: serializer.validated_data[key]
            for key, lookup in self.filter_mapping.items()
            if key in serializer.validated_data
        }
        return queryset.filter(**filters)
