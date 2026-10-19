"""Marketplace offers and their three package variants."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Offer(models.Model):
    """Store a business user's service listing."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="offers/", blank=True, null=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Provide stable newest-first listing order."""

        ordering = ["-updated_at", "-id"]

    def __str__(self):
        """Identify the offer in admin."""
        return self.title


class OfferDetail(models.Model):
    """Store one purchasable package belonging to an offer."""

    class Type(models.TextChoices):
        """Supported package tiers."""

        BASIC = "basic", "Basic"
        STANDARD = "standard", "Standard"
        PREMIUM = "premium", "Premium"

    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="details"
    )
    title = models.CharField(max_length=255)
    revisions = models.IntegerField(validators=[MinValueValidator(-1)])
    delivery_time_in_days = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    features = models.JSONField(default=list)
    offer_type = models.CharField(max_length=8, choices=Type.choices)

    class Meta:
        """Prevent duplicate tiers and invalid package numeric values."""

        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["offer", "offer_type"], name="unique_offer_tier"
            ),
            models.CheckConstraint(
                condition=models.Q(revisions__gte=-1),
                name="valid_offer_revisions",
            ),
            models.CheckConstraint(
                condition=models.Q(delivery_time_in_days__gte=1),
                name="positive_offer_delivery",
            ),
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="nonnegative_offer_price",
            ),
        ]

    def __str__(self):
        """Identify the package in admin."""
        return f"{self.title} ({self.offer_type})"
