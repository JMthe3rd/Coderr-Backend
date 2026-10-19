"""Real purchase fixtures shared by order API tests."""

from offers_app.tests.helpers import OfferTestCase
from orders_app.services import create_order


class OrderTestCase(OfferTestCase):
    """Prepare marketplace participants and one purchasable package."""

    def setUp(self):
        """Start tests as a customer with an available business offer."""
        super().setUp()
        self.offer = self.make_offer()
        self.package = self.offer.details.first()
        self.client.force_authenticate(self.customer)
        self.url = "/api/orders/"

    def make_order(self, customer=None, detail=None):
        """Create a real purchase snapshot through the order service."""
        return create_order(
            (detail or self.package).pk, customer or self.customer
        )

    def post_order(self, **extra):
        """Submit a purchase while optionally testing untrusted fields."""
        data = {"offer_detail_id": self.package.pk} | extra
        return self.client.post(self.url, data, format="json")
