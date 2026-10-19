"""Check that marketplace records remain usable in Django admin."""

from offers_app.tests.helpers import OfferTestCase
from orders_app.services import create_order
from reviews_app.services import create_review


class MarketplaceAdminTests(OfferTestCase):
    """Render real admin lists and change forms for all marketplace models."""

    def setUp(self):
        """Authenticate staff and prepare related marketplace records."""
        super().setUp()
        self.owner.is_staff = self.owner.is_superuser = True
        self.owner.save()
        self.client.force_login(self.owner)
        offer = self.make_offer()
        detail = offer.details.first()
        order = create_order(detail.pk, self.customer)
        review = self.make_review()
        self.records = [self.owner.profile, offer, detail, order, review]

    def make_review(self):
        """Create a real customer review for admin rendering."""
        return create_review(
            business_user=self.owner,
            reviewer=self.customer,
            rating=5,
            description="Admin smoke test",
        )

    def test_admin_lists_and_change_forms(self):
        """Render every marketplace model without template or form errors."""
        for record in self.records:
            base = (
                f"/admin/{record._meta.app_label}/{record._meta.model_name}/"
            )
            self.assertEqual(self.client.get(base).status_code, 200)
            response = self.client.get(f"{base}{record.pk}/change/")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, str(record), html=False)

    def test_order_admin_preserves_purchase_terms(self):
        """Allow status management but keep the purchase snapshot read-only."""
        order = self.records[3]
        response = self.client.get(
            f"/admin/orders_app/order/{order.pk}/change/"
        )
        fields = response.context["adminform"].form.fields
        self.assertEqual(set(fields), {"status"})
        self.assertEqual(
            self.client.get("/admin/orders_app/order/add/").status_code, 403
        )

    def test_admin_requires_session_authentication(self):
        """Do not expose admin records to anonymous visitors."""
        self.client.logout()
        self.assertEqual(self.client.get("/admin/").status_code, 302)
