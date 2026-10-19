"""Account creation operations."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import UserProfile


@transaction.atomic
def register_user(validated_data):
    """Create the account and its role profile in one transaction."""
    data = validated_data.copy()
    role = data.pop("type")
    data.pop("repeated_password")
    user = get_user_model().objects.create_user(**data)
    UserProfile.objects.create(user=user, type=role)
    return user


@transaction.atomic
def update_profile(profile, validated_data):
    """Persist user and profile changes together after validation."""
    user_data = validated_data.pop("user", {})
    for field, value in user_data.items():
        setattr(profile.user, field, value)
    if user_data:
        profile.user.save(update_fields=list(user_data))
    if "file" in validated_data:
        profile.uploaded_at = timezone.now()
    for field, value in validated_data.items():
        setattr(profile, field, value)
    profile.save()
    return profile
