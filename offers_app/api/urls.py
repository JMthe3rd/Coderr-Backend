"""Offer and package resource routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OfferDetailView, OfferViewSet

router = DefaultRouter()
router.register("offers", OfferViewSet, basename="offer")
urlpatterns = [
    path("", include(router.urls)),
    path(
        "offerdetails/<int:pk>/",
        OfferDetailView.as_view(),
        name="offer-detail-package",
    ),
]
