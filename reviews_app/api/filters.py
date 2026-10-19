"""Validated business and reviewer filtering for review lists."""

from rest_framework import serializers
from rest_framework.filters import BaseFilterBackend


class ReviewQuerySerializer(serializers.Serializer):
    """Validate integer account identifiers used as optional filters."""

    business_user_id = serializers.IntegerField(required=False, min_value=1)
    reviewer_id = serializers.IntegerField(required=False, min_value=1)


class ReviewFilterBackend(BaseFilterBackend):
    """Filter the review listing by validated account IDs."""

    def filter_queryset(self, request, queryset, view):
        """Reject malformed filters before applying them to the queryset."""
        serializer = ReviewQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return queryset.filter(**serializer.validated_data)
