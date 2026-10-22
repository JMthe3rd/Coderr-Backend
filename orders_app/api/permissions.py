"""Customer purchases, business status updates and staff order deletion."""

from rest_framework.permissions import BasePermission


class OrderPermission(BasePermission):
    """Check purchase roles and permissions on existing orders."""

    def has_permission(self, request, view):
        """Require a customer profile to place a new order."""
        if view.action != "create":
            return True
        profile = getattr(request.user, "profile", None)
        return profile is not None and profile.type == "customer"

    def has_object_permission(self, request, view, obj):
        """Check write access after DRF has found the requested order."""
        if view.action == "partial_update":
            profile = getattr(request.user, "profile", None)
            return (
                profile is not None
                and profile.type == "business"
                and obj.business_user_id == request.user.pk
            )
        return view.action == "destroy" and request.user.is_staff
