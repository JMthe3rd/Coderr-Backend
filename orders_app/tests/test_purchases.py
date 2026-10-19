"""Order creation, immutable package snapshots and participant-only lists."""

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from orders_app.models import Order

from .helpers import OrderTestCase


class PurchaseTests(OrderTestCase):
    """Verify authoritative source data and role-restricted purchases."""

    def test_purchase_response(self):
        """Return a complete snapshot and the documented initial status."""
        response = self.post_order()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["customer_user"], self.customer.pk)
        self.assertEqual(response.data["business_user"], self.owner.pk)
        self.assertEqual(response.data["status"], "in_progress")
        self.assertEqual(response.data["price"], 100)
        self.assertEqual(response.data["title"], self.package.title)
        self.assertEqual(response.data["features"], self.package.features)
        self.assertNotIn("offer_detail_id", response.data)

    def test_untrusted_snapshot_and_identity_fields(self):
        """Ignore forged prices, participants and initial status."""
        response = self.post_order(
            price=1,
            customer_user=self.other.pk,
            business_user=self.customer.pk,
            status="completed",
            title="Forged",
        )
        self.assertEqual(response.status_code, 201)
        self.assert_authoritative_order(Order.objects.get())

    def assert_authoritative_order(self, order):
        """Check server-derived participants and purchased terms."""
        self.assertEqual(order.price, 100)
        self.assertEqual(order.customer_user, self.customer)
        self.assertEqual(order.business_user, self.owner)
        self.assertEqual(order.status, "in_progress")
        self.assertEqual(order.title, self.package.title)

    def test_creation_requires_customer_profile(self):
        """Reject anonymous, business and profile-less accounts."""
        bare = get_user_model().objects.create_user(username="bare")
        for user, expected in [(None, 401), (self.owner, 403), (bare, 403)]:
            self.client.force_authenticate(user)
            self.assertEqual(self.post_order().status_code, expected)
        self.assertFalse(Order.objects.exists())

    def test_invalid_and_missing_package_ids(self):
        """Differentiate invalid input from a missing package resource."""
        for value in [None, "invalid", 0, -1, 1.5]:
            self.assertEqual(
                self.post_order(offer_detail_id=value).status_code, 400
            )
        self.assertEqual(
            self.post_order(offer_detail_id=99999).status_code, 404
        )
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_snapshot_survives_source_edits_and_deletion(self):
        """Keep purchased terms when the offer changes or disappears."""
        order = self.make_order()
        before = Order.objects.values().get(pk=order.pk)
        self.package.title = "Changed"
        self.package.price = 999
        self.package.features = ["Different terms"]
        self.package.save()
        self.assertEqual(Order.objects.values().get(pk=order.pk), before)
        self.offer.delete()
        self.assertEqual(Order.objects.values().get(pk=order.pk), before)

    def test_repeated_purchases_are_independent(self):
        """Allow multiple purchases without sharing mutable features lists."""
        first = self.make_order()
        second = self.make_order()
        first.features.append("Local change")
        second.refresh_from_db()
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(second.features, self.package.features)

    def test_token_authenticated_purchase(self):
        """Exercise the real authentication header for order creation."""
        token = Token.objects.create(user=self.customer)
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(self.post_order().status_code, 201)


class OrderListTests(OrderTestCase):
    """Restrict unpaginated lists to the authenticated participant."""

    def test_customer_and_business_see_their_order(self):
        """Show the order to both participants with the same response shape."""
        order = self.make_order()
        for user in [self.customer, self.owner]:
            self.client.force_authenticate(user)
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertIsInstance(response.data, list)
            self.assertEqual([row["id"] for row in response.data], [order.pk])

    def test_foreign_orders_remain_hidden_even_from_staff_lists(self):
        """Give staff deletion rights without a global purchase listing."""
        self.make_order()
        self.other.is_staff = True
        self.other.save()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url).data, [])

    def test_mixed_orders_are_filtered(self):
        """Include the customer's purchases but hide unrelated purchases."""
        own = self.make_order()
        another = self.make_user("another", "customer")
        self.make_order(customer=another)
        response = self.client.get(self.url)
        self.assertEqual([row["id"] for row in response.data], [own.pk])

    def test_anonymous_list(self):
        """Require authentication even when no orders exist."""
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
