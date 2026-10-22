"""Participant purchases, status changes and business order counts."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from auth_app.models import UserProfile
from orders_app.models import Order

from .permissions import OrderPermission
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusSerializer,
)


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """List purchases and handle order creation, status edits and deletion."""

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, OrderPermission]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        """Restrict lists to participants; check write ownership separately."""
        queryset = super().get_queryset()
        if self.action == "list":
            user = self.request.user
            return queryset.filter(
                Q(customer_user=user) | Q(business_user=user)
            )
        return queryset

    def get_serializer_class(self):
        """Validate purchase data for POST and order status for PATCH."""
        serializers = {
            "create": OrderCreateSerializer,
            "partial_update": OrderStatusSerializer,
        }
        return serializers.get(self.action, self.serializer_class)

    def perform_create(self, serializer):
        """Set the customer from the authenticated user."""
        serializer.save(customer_user=self.request.user)


class OrderCountView(APIView):
    """Count running orders for an existing business user."""

    permission_classes = [IsAuthenticated]
    order_status = Order.Status.IN_PROGRESS
    response_field = "order_count"

    def get(self, request, business_user_id):
        """Return zero for an empty business account and 404 for other IDs."""
        get_object_or_404(
            UserProfile, user_id=business_user_id, type="business"
        )
        count = Order.objects.filter(
            business_user_id=business_user_id, status=self.order_status
        ).count()
        return Response({self.response_field: count})


class CompletedOrderCountView(OrderCountView):
    """Return completed_order_count for a business account."""

    order_status = Order.Status.COMPLETED
    response_field = "completed_order_count"
