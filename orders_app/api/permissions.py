"""Marketplace role and object ownership rules for orders."""

from rest_framework.permissions import BasePermission


class OrderPermission(BasePermission):
    """Restrict purchase creation, status changes and deletion by role."""

    def has_permission(self, request, view):
        """Enforce role requirements after authentication has succeeded."""
        if view.action == "destroy":
            return request.user.is_staff
        roles = {"create": "customer", "partial_update": "business"}
        if view.action not in roles:
            return True
        profile = getattr(request.user, "profile", None)
        return profile is not None and profile.type == roles[view.action]

    def has_object_permission(self, request, view, obj):
        """Limit status changes to the order's business participant."""
        if view.action == "partial_update":
            return obj.business_user_id == request.user.pk
        return view.action == "destroy" and request.user.is_staff
