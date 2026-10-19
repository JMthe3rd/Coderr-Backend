"""Review fixtures using real customer and business accounts."""

from offers_app.tests.helpers import OfferTestCase
from reviews_app.services import create_review


class ReviewTestCase(OfferTestCase):
    """Prepare review participants without requiring prior purchases."""

    def setUp(self):
        """Authenticate the customer for review creation tests."""
        super().setUp()
        self.client.force_authenticate(self.customer)
        self.url = "/api/reviews/"

    def post_review(self, **changes):
        """Submit a valid review with optional overridden input fields."""
        data = {
            "business_user": self.owner.pk,
            "rating": 4,
            "description": "Excellent work",
        } | changes
        return self.client.post(self.url, data, format="json")

    def make_review(self, business=None, reviewer=None, rating=4):
        """Create a persisted review through the uniqueness-aware service."""
        return create_review(
            business_user=business or self.owner,
            reviewer=reviewer or self.customer,
            rating=rating,
            description="Excellent work",
        )
