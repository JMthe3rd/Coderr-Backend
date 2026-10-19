"""Customer creation and author-only review modification rules."""

from rest_framework.permissions import BasePermission


class ReviewPermission(BasePermission):
    """Allow authenticated reads, customer creation and author writes."""

    def has_permission(self, request, view):
        """Require a customer profile only when creating a review."""
        if view.action != "create":
            return True
        profile = getattr(request.user, "profile", None)
        return profile is not None and profile.type == "customer"

    def has_object_permission(self, request, view, obj):
        """Keep foreign reviews protected even from marketplace staff."""
        return obj.reviewer_id == request.user.pk
