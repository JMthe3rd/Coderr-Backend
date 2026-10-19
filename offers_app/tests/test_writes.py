"""Offer validation, access control and nested update regression tests."""

from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError

from offers_app.models import Offer, OfferDetail
from offers_app.services import create_offer, update_offer

from .helpers import OfferTestCase, offer_payload


class OfferCreateTests(OfferTestCase):
    """Require business ownership and exactly three valid packages."""

    def test_creation_contract(self):
        """Return full package data and derive owner from authentication."""
        response = self.post_offer(offer_payload() | {"user": self.other.pk})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Offer.objects.get().user, self.owner)
        self.assertEqual(
            set(response.data),
            {"id", "title", "image", "description", "details"},
        )
        self.assertEqual(len(response.data["details"]), 3)
        self.assertEqual(response.data["details"][0]["price"], 100)
        self.assertEqual(response.data["details"][0]["revisions"], -1)

    def test_creation_role_permissions(self):
        """Reject anonymous users, customers and accounts without profiles."""
        bare = get_user_model().objects.create_user(username="bare")
        for user, expected in [(None, 401), (self.customer, 403), (bare, 403)]:
            self.client.force_authenticate(user)
            self.assertEqual(self.post_offer().status_code, expected)
        self.assertFalse(Offer.objects.exists())

    def test_missing_duplicate_and_unknown_tiers(self):
        """Reject incomplete, duplicate and invalid tier combinations."""
        for tiers in [
            [],
            ["basic"],
            ["basic", "basic", "premium"],
            ["basic", "standard", "invalid"],
        ]:
            data = offer_payload()
            data["details"] = [deepcopy(data["details"][0]) for _ in tiers]
            for detail, tier in zip(data["details"], tiers):
                detail["offer_type"] = tier
            self.assertEqual(self.post_offer(data).status_code, 400)
        self.assertFalse(OfferDetail.objects.exists())

    def test_invalid_package_fields(self):
        """Reject numeric boundaries and malformed prices."""
        changes = [
            {"revisions": -2},
            {"delivery_time_in_days": 0},
            {"price": -1},
            {"price": "NaN"},
            {"price": "1.234"},
        ]
        for change in changes:
            data = offer_payload()
            data["details"][0].update(change)
            self.assertEqual(self.post_offer(data).status_code, 400)
        self.assertFalse(Offer.objects.exists())

    def test_missing_fields(self):
        """Require offer data and complete package fields during creation."""
        for field in ["title", "description", "details"]:
            data = offer_payload()
            data.pop(field)
            self.assertEqual(self.post_offer(data).status_code, 400)
        data = offer_payload()
        data["details"][0].pop("price")
        self.assertEqual(self.post_offer(data).status_code, 400)

    def test_non_object_requests(self):
        """Reject JSON lists and scalar values with a client error."""
        for data in [[], [1], "invalid", 42]:
            response = self.client.post(self.url, data, format="json")
            self.assertEqual(response.status_code, 400)

    def test_creation_transaction_rolls_back(self):
        """Do not retain an offer if package persistence fails."""
        with patch(
            "offers_app.services.OfferDetail.objects.create",
            side_effect=IntegrityError("simulated storage failure"),
        ):
            with self.assertRaises(IntegrityError):
                create_offer(offer_payload() | {"user": self.owner})
        self.assertFalse(Offer.objects.exists())


class OfferUpdateTests(OfferTestCase):
    """Verify partial updates, immutable tier IDs and ownership."""

    def setUp(self):
        """Create one offer to update or delete."""
        super().setUp()
        self.offer = self.make_offer()
        self.url = f"/api/offers/{self.offer.pk}/"

    def test_partial_package_update_preserves_other_values(self):
        """Update one package price without replacing rows or other fields."""
        before = list(self.offer.details.values_list("id", "title", "price"))
        data = {"details": [{"offer_type": "basic", "price": "125.50"}]}
        response = self.client.patch(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        after = list(self.offer.details.values_list("id", "title", "price"))
        self.assertEqual(
            [row[:2] for row in before], [row[:2] for row in after]
        )
        self.assertEqual(before[1:], after[1:])
        self.assertEqual(response.data["details"][0]["price"], 125.50)
        self.assertEqual(len(response.data["details"]), 3)

    def test_invalid_update_leaves_offer_unchanged(self):
        """Validate all packages before persisting any parent changes."""
        for details in [
            [{"price": 120}],
            [{"offer_type": "basic", "id": 999}],
            [{"offer_type": "basic", "price": -1}],
            [{"offer_type": "basic"}, {"offer_type": "basic"}],
        ]:
            data = {"title": "Changed", "details": details}
            response = self.client.patch(self.url, data, format="json")
            self.assertEqual(response.status_code, 400)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.title, "Website Design")

    def test_title_only_patch(self):
        """Allow partial parent changes without resubmitting details."""
        response = self.client.patch(
            self.url, {"title": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Changed")
        self.assertEqual(response.data["description"], self.offer.description)
        self.assertEqual(self.offer.details.count(), 3)

    def test_foreign_writes_and_anonymous_writes(self):
        """Reject foreign owners and customers for both edit and delete."""
        for user, expected in [
            (self.other, 403),
            (self.customer, 403),
            (None, 401),
        ]:
            self.client.force_authenticate(user)
            self.assert_write_status(expected)
        self.assertTrue(Offer.objects.filter(pk=self.offer.pk).exists())

    def assert_write_status(self, expected):
        """Require the same access decision for both write operations."""
        self.assertEqual(self.client.patch(self.url, {}).status_code, expected)
        self.assertEqual(self.client.delete(self.url).status_code, expected)

    def test_delete_cascades_packages(self):
        """Return an empty 204 response and remove dependent packages."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(OfferDetail.objects.exists())

    def test_update_transaction_rolls_back(self):
        """Roll back the parent when a nested package write fails."""
        data = {"title": "Changed", "details": [{"offer_type": "basic"}]}
        with patch(
            "offers_app.services.update_detail", side_effect=IntegrityError
        ):
            with self.assertRaises(IntegrityError):
                update_offer(self.offer, data)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.title, "Website Design")
