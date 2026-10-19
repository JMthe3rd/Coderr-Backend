"""Authenticated profile detail and role-specific list endpoints."""

from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from auth_app.models import UserProfile

from .permissions import IsProfileOwnerOrReadOnly
from .profile_serializers import (
    BusinessProfileSerializer,
    CustomerProfileSerializer,
    ProfileSerializer,
)


class ProfileView(RetrieveUpdateAPIView):
    """Read any profile and partially update the authenticated user's own."""

    queryset = UserProfile.objects.select_related("user")
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, IsProfileOwnerOrReadOnly]
    lookup_field = "user_id"
    lookup_url_kwarg = "pk"
    http_method_names = ["get", "patch", "head", "options"]


class BusinessProfileListView(ListAPIView):
    """List business profiles without pagination or private email data."""

    queryset = (
        UserProfile.objects.select_related("user")
        .filter(type="business")
        .order_by("user_id")
    )
    serializer_class = BusinessProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class CustomerProfileListView(ListAPIView):
    """List compact customer profiles without pagination."""

    queryset = (
        UserProfile.objects.select_related("user")
        .filter(type="customer")
        .order_by("user_id")
    )
    serializer_class = CustomerProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
