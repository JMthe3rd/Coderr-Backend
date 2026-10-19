"""Review persistence with race-safe duplicate protection."""

from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied

from .models import Review


def create_review(**validated_data):
    """Reject duplicate reviewer/business pairs with HTTP 403."""
    pair = {key: validated_data[key] for key in ["business_user", "reviewer"]}
    try:
        with transaction.atomic():
            return Review.objects.create(**validated_data)
    except IntegrityError:
        if Review.objects.filter(**pair).exists():
            raise PermissionDenied("You have already reviewed this business.")
        raise
