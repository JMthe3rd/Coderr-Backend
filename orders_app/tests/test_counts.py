"""Authenticated business-user counters separated by order status."""

from django.contrib.auth import get_user_model

from .helpers import OrderTestCase


class OrderCountTests(OrderTestCase):
    """Count only the requested business and the selected order status."""

    def setUp(self):
        """Prepare counters and one order for each lifecycle state."""
        super().setUp()
        self.urls = [
            f"/api/order-count/{self.owner.pk}/",
            f"/api/completed-order-count/{self.owner.pk}/",
        ]
        self.make_order()
        completed = self.make_order()
        completed.status = "completed"
        completed.save()
        cancelled = self.make_order()
        cancelled.status = "cancelled"
        cancelled.save()

    def test_counts_exclude_other_statuses_and_businesses(self):
        """Exclude cancelled orders and orders placed with another provider."""
        other_package = self.make_offer(user=self.other).details.first()
        self.make_order(detail=other_package)
        for url, key in zip(
            self.urls, ["order_count", "completed_order_count"]
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {key: 1})

    def test_empty_business_counts_are_zero(self):
        """Return zero instead of 404 for a business with no purchases."""
        for prefix, key in [
            ("order-count", "order_count"),
            ("completed-order-count", "completed_order_count"),
        ]:
            response = self.client.get(f"/api/{prefix}/{self.other.pk}/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {key: 0})

    def test_missing_customer_and_profileless_ids(self):
        """Return 404 when the target is not an existing business profile."""
        bare = get_user_model().objects.create_user(username="bare")
        for pk in [99999, self.customer.pk, bare.pk]:
            for prefix in ["order-count", "completed-order-count"]:
                response = self.client.get(f"/api/{prefix}/{pk}/")
                self.assertEqual(response.status_code, 404)

    def test_anonymous_counts(self):
        """Require authentication for both counter endpoints."""
        self.client.force_authenticate(None)
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 401)

    def test_status_change_updates_both_counters(self):
        """Move an order from running to completed through the actual API."""
        order = self.owner.business_orders.get(status="in_progress")
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/orders/{order.pk}/", {"status": "completed"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get(self.urls[0]).data, {"order_count": 0}
        )
        self.assertEqual(
            self.client.get(self.urls[1]).data, {"completed_order_count": 2}
        )
