"""Order resources and business-user order statistics."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CompletedOrderCountView, OrderCountView, OrderViewSet

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")
urlpatterns = [
    path("", include(router.urls)),
    path(
        "order-count/<int:business_user_id>/",
        OrderCountView.as_view(),
        name="order-count",
    ),
    path(
        "completed-order-count/<int:business_user_id>/",
        CompletedOrderCountView.as_view(),
        name="completed-order-count",
    ),
]
