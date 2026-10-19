"""Explicit review representations and editable-field validation."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from reviews_app.models import Review
from reviews_app.services import create_review


class ReviewSerializer(serializers.ModelSerializer):
    """Accept business targets while deriving reviewer from authentication."""

    business_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(profile__type="business")
    )

    class Meta:
        """Declare fields with duplicate handling delegated to the service."""

        model = Review
        fields = [
            "id",
            "business_user",
            "reviewer",
            "rating",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "reviewer", "created_at", "updated_at"]
        validators = []

    def create(self, validated_data):
        """Enforce uniqueness through the database-backed review service."""
        return create_review(**validated_data)


class ReviewUpdateSerializer(ReviewSerializer):
    """Only permit rating and description changes on existing reviews."""

    business_user = serializers.PrimaryKeyRelatedField(read_only=True)

    def validate(self, attrs):
        """Reject empty updates and changes to identity or ownership."""
        if not attrs or set(self.initial_data) - {"rating", "description"}:
            raise serializers.ValidationError(
                "Update rating and/or description only."
            )
        return attrs
