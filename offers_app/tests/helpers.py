"""Reusable realistic offer fixtures for API tests."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from auth_app.models import UserProfile
from offers_app.services import create_offer


def offer_payload(title="Website Design"):
    """Return a complete offer with three differently priced tiers."""
    return {
        "title": title,
        "description": "Professional web development",
        "details": [
            package(tier, price, days)
            for tier, price, days in [
                ("basic", "100.00", 5),
                ("standard", "200.00", 7),
                ("premium", "500.00", 10),
            ]
        ],
    }


def package(tier, price, days):
    """Return valid package data with unlimited revisions supported."""
    return {
        "title": f"{tier} package",
        "revisions": -1,
        "delivery_time_in_days": days,
        "price": price,
        "features": ["Design", "Implementation"],
        "offer_type": tier,
    }


class OfferTestCase(APITestCase):
    """Prepare marketplace roles without coupling tests to registration."""

    def setUp(self):
        """Create owner, other business and customer accounts."""
        self.owner = self.make_user("owner", "business")
        self.other = self.make_user("other", "business")
        self.customer = self.make_user("customer", "customer")
        self.client.force_authenticate(self.owner)
        self.url = "/api/offers/"

    def make_user(self, username, role):
        """Create an account and its marketplace role."""
        user = get_user_model().objects.create_user(username=username)
        UserProfile.objects.create(user=user, type=role)
        return user

    def make_offer(self, title="Website Design", user=None):
        """Persist a complete offer for read and update tests."""
        return create_offer(
            offer_payload(title) | {"user": user or self.owner}
        )

    def post_offer(self, payload=None):
        """Submit offer creation as JSON."""
        return self.client.post(
            self.url, payload or offer_payload(), format="json"
        )
