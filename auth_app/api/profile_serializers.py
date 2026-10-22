"""Profile representations and validated partial updates."""

from rest_framework import serializers

from auth_app.models import UserProfile
from auth_app.services import update_profile


class BusinessProfileSerializer(serializers.ModelSerializer):
    """Return business contact details and profile information in lists."""

    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(
        source="user.first_name", allow_blank=True, max_length=150
    )
    last_name = serializers.CharField(
        source="user.last_name", allow_blank=True, max_length=150
    )
    file = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        """Declare business profile fields explicitly."""

        model = UserProfile
        fields = [
            "user",
            "username",
            "first_name",
            "last_name",
            "file",
            "location",
            "tel",
            "description",
            "working_hours",
            "type",
        ]
        read_only_fields = ["user", "type"]


class ProfileSerializer(BusinessProfileSerializer):
    """Represent profile details and validate editable user fields."""

    email = serializers.EmailField(source="user.email", max_length=254)

    class Meta(BusinessProfileSerializer.Meta):
        """Add email and immutable creation time for the detail endpoint."""

        fields = BusinessProfileSerializer.Meta.fields + [
            "email",
            "created_at",
        ]
        read_only_fields = ["user", "type", "created_at"]

    def validate_file(self, value):
        """Allow common raster images of at most five megabytes."""
        if value is None:
            return value
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Maximum image size is 5 MB.")
        if value.image.format not in {"JPEG", "PNG", "WEBP"}:
            raise serializers.ValidationError("Use a JPEG, PNG or WebP image.")
        return value

    def update(self, instance, validated_data):
        """Save nested user fields through the atomic profile service."""
        return update_profile(instance, validated_data)


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Return customer names, avatars and avatar upload timestamps."""

    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(
        source="user.first_name", read_only=True
    )
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        """Declare customer list fields explicitly."""

        model = UserProfile
        fields = [
            "user",
            "username",
            "first_name",
            "last_name",
            "file",
            "uploaded_at",
            "type",
        ]
