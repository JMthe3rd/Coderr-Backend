"""Object permissions for account profiles."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsProfileOwnerOrReadOnly(BasePermission):
    """Permit authenticated readers and restrict writes to the owner."""

    def has_object_permission(self, request, view, obj):
        """Compare ownership with the profile's user ID."""
        return request.method in SAFE_METHODS or obj.user_id == request.user.pk
