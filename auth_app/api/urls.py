"""Account API routes."""

from django.urls import path

from .profile_views import (
    BusinessProfileListView,
    CustomerProfileListView,
    ProfileView,
)
from .views import LoginView, RegistrationView

urlpatterns = [
    path("profile/<int:pk>/", ProfileView.as_view(), name="profile-detail"),
    path(
        "profiles/business/",
        BusinessProfileListView.as_view(),
        name="business-profiles",
    ),
    path(
        "profiles/customer/",
        CustomerProfileListView.as_view(),
        name="customer-profiles",
    ),
    path("registration/", RegistrationView.as_view(), name="registration"),
    path("login/", LoginView.as_view(), name="login"),
]
