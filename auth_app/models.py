"""Account profile data."""

from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Store a user's marketplace role and public profile information."""

    class Type(models.TextChoices):
        """Supported marketplace roles."""

        CUSTOMER = "customer", "Customer"
        BUSINESS = "business", "Business"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    type = models.CharField(max_length=8, choices=Type.choices)
    file = models.ImageField(upload_to="profiles/", blank=True)
    location = models.CharField(max_length=255, blank=True, default="")
    tel = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")
    working_hours = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        """Identify the profile in Django admin."""
        return f"{self.user.username} ({self.type})"
