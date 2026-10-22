"""Offer CRUD endpoints and authenticated package retrieval."""

from django.db.models import Min
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from offers_app.models import Offer, OfferDetail

from .filters import OfferFilterBackend
from .pagination import OfferPagination
from .permissions import OfferPermission
from .serializers import (
    OfferDetailSerializer,
    OfferListSerializer,
    OfferReadSerializer,
    OfferWriteSerializer,
)


class OfferViewSet(ModelViewSet):
    """List service offers and let business users manage their own offers."""

    queryset = (
        Offer.objects.select_related("user")
        .prefetch_related("details")
        .annotate(
            min_price=Min("details__price"),
            min_delivery_time=Min("details__delivery_time_in_days"),
        )
    )
    serializer_class = OfferReadSerializer
    permission_classes = [OfferPermission]
    pagination_class = OfferPagination
    filter_backends = [OfferFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["updated_at", "min_price"]
    ordering = ["-updated_at", "-id"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        """Choose expanded write responses and linked read responses."""
        if self.action in {"create", "partial_update"}:
            return OfferWriteSerializer
        if self.action == "list":
            return OfferListSerializer
        return self.serializer_class

    def filter_queryset(self, queryset):
        """Apply query filters only to the public list."""
        if self.action == "list":
            return super().filter_queryset(queryset)
        return queryset

    def perform_create(self, serializer):
        """Set ownership from authentication rather than request data."""
        serializer.save(user=self.request.user)


class OfferDetailView(RetrieveAPIView):
    """Retrieve the full package data for an authenticated user."""

    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailSerializer
    permission_classes = [IsAuthenticated]
