"""Immutable purchase snapshots with a separately editable order status."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from offers_app.models import OfferDetail


class Order(models.Model):
    """Preserve the purchased package independently of its source offer."""

    class Status(models.TextChoices):
        """Order status values: in progress, completed and cancelled."""

        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_orders",
    )
    business_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_orders",
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
    offer_type = models.CharField(
        max_length=8, choices=OfferDetail.Type.choices
    )
    status = models.CharField(
        max_length=11, choices=Status.choices, default=Status.IN_PROGRESS
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Order results consistently and enforce valid purchase values."""

        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(revisions__gte=-1),
                name="valid_order_revisions",
            ),
            models.CheckConstraint(
                condition=models.Q(delivery_time_in_days__gte=1),
                name="positive_order_delivery",
            ),
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="nonnegative_order_price",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["in_progress", "completed", "cancelled"]
                ),
                name="valid_order_status",
            ),
        ]

    def __str__(self):
        """Identify the order and its status in admin."""
        return f"{self.title} ({self.status})"
