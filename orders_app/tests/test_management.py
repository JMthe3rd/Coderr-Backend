"""Order status ownership, immutable purchase terms and staff deletion."""

from django.contrib.auth import get_user_model

from orders_app.models import Order

from .helpers import OrderTestCase


class OrderManagementTests(OrderTestCase):
    """Exercise all authorized and denied order write operations."""

    def setUp(self):
        """Prepare an existing purchase and authenticate its business owner."""
        super().setUp()
        self.order = self.make_order()
        self.url = f"/api/orders/{self.order.pk}/"
        self.client.force_authenticate(self.owner)

    def patch_status(self, status):
        """Submit a status-only partial update."""
        return self.client.patch(self.url, {"status": status}, format="json")

    def test_all_documented_statuses(self):
        """Change only status and update time, preserving purchased terms."""
        before = self.order.created_at
        for status in ["completed", "cancelled", "in_progress"]:
            response = self.patch_status(status)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["status"], status)
        self.order.refresh_from_db()
        self.assertEqual(self.order.created_at, before)
        self.assertGreater(self.order.updated_at, before)
        self.assertEqual(self.order.price, self.package.price)

    def test_invalid_status_and_forbidden_fields(self):
        """Return 400 without changing the order for unsupported input."""
        for data in [
            {},
            {"status": "invalid"},
            {"status": None},
            {"status": "completed", "price": 1},
            {"status": "completed", "business_user": self.other.pk},
            {"status": "completed", "extra": "unknown"},
        ]:
            response = self.client.patch(self.url, data, format="json")
            self.assertEqual(response.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "in_progress")

    def test_status_permissions(self):
        """Deny status changes by customers, unrelated businesses or staff."""
        self.other.is_staff = True
        self.other.save()
        for user, expected in [
            (self.customer, 403),
            (self.other, 403),
            (None, 401),
        ]:
            self.client.force_authenticate(user)
            self.assert_status_denied(expected)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "in_progress")

    def assert_status_denied(self, expected):
        """Check denied status edits without changing persisted order state."""
        self.assertEqual(self.patch_status("completed").status_code, expected)

    def test_profileless_status_change(self):
        """Deny status changes for an account without a marketplace profile."""
        bare = get_user_model().objects.create_user(username="bare")
        self.client.force_authenticate(bare)
        self.assert_status_denied(403)

    def test_non_staff_cannot_delete(self):
        """Neither participant may delete unless explicitly marked staff."""
        for user, expected in [
            (self.owner, 403),
            (self.customer, 403),
            (None, 401),
        ]:
            self.client.force_authenticate(user)
            self.assertEqual(
                self.client.delete(self.url).status_code, expected
            )
        self.assertTrue(Order.objects.filter(pk=self.order.pk).exists())

    def test_staff_without_profile_can_delete_unrelated_order(self):
        """Authorize staff without requiring a marketplace profile."""
        staff = get_user_model().objects.create_user(
            username="staff", is_staff=True
        )
        self.client.force_authenticate(staff)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(Order.objects.filter(pk=self.order.pk).exists())
        self.assertTrue(self.offer.details.filter(pk=self.package.pk).exists())

    def test_missing_orders_return_404_for_authenticated_roles(self):
        """Look up missing orders before checking edit or delete privileges."""
        bare = get_user_model().objects.create_user(username="missing_bare")
        staff = get_user_model().objects.create_user(
            username="missing_staff", is_staff=True
        )
        self.url = "/api/orders/99999/"
        for user in [self.customer, self.owner, self.other, bare, staff]:
            self.client.force_authenticate(user)
            self.assertEqual(self.patch_status("completed").status_code, 404)
            self.assertEqual(self.client.delete(self.url).status_code, 404)

    def test_missing_orders_still_require_authentication(self):
        """Return 401 for anonymous writes even when the order is missing."""
        self.url = "/api/orders/99999/"
        self.client.force_authenticate(None)
        self.assertEqual(self.patch_status("completed").status_code, 401)
        self.assertEqual(self.client.delete(self.url).status_code, 401)

    def test_business_participant_requires_business_profile(self):
        """Deny status edits if the provider no longer has a business role."""
        profile = self.owner.profile
        profile.type = "customer"
        profile.save()
        self.assert_status_denied(403)
        profile.delete()
        self.owner.refresh_from_db()
        self.assert_status_denied(403)

    def test_unsupported_methods(self):
        """Return 405 for single-order GET requests and PUT replacement."""
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.client.put(self.url, {}).status_code, 405)
