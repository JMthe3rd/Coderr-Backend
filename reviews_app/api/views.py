"""Authenticated review listing and author-controlled review writes."""

from rest_framework import mixins
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from reviews_app.models import Review

from .filters import ReviewFilterBackend
from .permissions import ReviewPermission
from .serializers import ReviewSerializer, ReviewUpdateSerializer


class ReviewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """Expose list, create, PATCH and DELETE without undocumented retrieval."""

    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated, ReviewPermission]
    pagination_class = None
    filter_backends = [ReviewFilterBackend, OrderingFilter]
    ordering_fields = ["updated_at", "rating"]
    ordering = ["-updated_at", "-id"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        """Choose strict editable fields for partial updates."""
        if self.action == "partial_update":
            return ReviewUpdateSerializer
        return self.serializer_class

    def filter_queryset(self, queryset):
        """Apply optional query filters only to the review list."""
        if self.action == "list":
            return super().filter_queryset(queryset)
        return queryset

    def perform_create(self, serializer):
        """Derive reviewer identity from the authenticated account."""
        serializer.save(reviewer=self.request.user)
