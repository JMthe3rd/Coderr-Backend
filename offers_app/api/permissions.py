"""Offer role and ownership access control."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class OfferPermission(BasePermission):
    """Allow public listings, authenticated reads and owner-only writes."""

    def has_permission(self, request, view):
        """Require a business profile for offer creation."""
        if view.action == "list":
            return True
        if not request.user.is_authenticated:
            return False
        if view.action == "create":
            profile = getattr(request.user, "profile", None)
            return profile is not None and profile.type == "business"
        return True

    def has_object_permission(self, request, view, obj):
        """Permit object writes only by the offer creator."""
        return request.method in SAFE_METHODS or obj.user_id == request.user.pk
