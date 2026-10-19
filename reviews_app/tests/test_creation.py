"""Review roles, target validation and database-backed duplicate protection."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from reviews_app.models import Review
from reviews_app.services import create_review

from .helpers import ReviewTestCase


class ReviewCreationTests(ReviewTestCase):
    """Create valid ratings while protecting author identity and uniqueness."""

    def test_creation_contract_and_author_identity(self):
        """Create the review without trusting a forged reviewer ID."""
        response = self.post_review(reviewer=self.other.pk)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["reviewer"], self.customer.pk)
        self.assertEqual(response.data["business_user"], self.owner.pk)
        self.assertEqual(response.data["rating"], 4)
        fields = (
            "id business_user reviewer rating description "
            "created_at updated_at"
        )
        self.assertEqual(set(response.data), set(fields.split()))

    def test_creation_requires_customer(self):
        """Reject anonymous users, business users and profile-less users."""
        bare = get_user_model().objects.create_user(username="bare")
        for user, expected in [(None, 401), (self.owner, 403), (bare, 403)]:
            self.client.force_authenticate(user)
            self.assertEqual(self.post_review().status_code, expected)
        self.assertFalse(Review.objects.exists())

    def test_rating_boundaries_and_invalid_values(self):
        """Reject ratings outside 1 to 5 and fractional or missing values."""
        for rating in [0, 6, -1, 1.5, "invalid", None]:
            self.assertEqual(self.post_review(rating=rating).status_code, 400)
        self.assertFalse(Review.objects.exists())
        self.assertEqual(self.post_review(rating=1).status_code, 201)
        self.assertEqual(
            self.post_review(
                business_user=self.other.pk, rating=5
            ).status_code,
            201,
        )

    def test_target_must_be_existing_business(self):
        """Reject customer, missing and profile-less business targets."""
        bare = get_user_model().objects.create_user(username="bare")
        for target in [self.customer.pk, bare.pk, 99999, "invalid", None]:
            self.assertEqual(
                self.post_review(business_user=target).status_code, 400
            )
        self.assertFalse(Review.objects.exists())

    def test_missing_fields_and_empty_description(self):
        """Require creation inputs and a nonempty description."""
        for data in [
            {},
            {"business_user": self.owner.pk, "rating": 4},
            {"business_user": self.owner.pk, "description": "Text"},
        ]:
            response = self.client.post(self.url, data, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.post_review(description="").status_code, 400)

    def test_duplicate_returns_403_and_preserves_original(self):
        """Retain the original rating when rejecting duplicate reviews."""
        original = self.make_review()
        response = self.post_review(rating=1)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Review.objects.count(), 1)
        original.refresh_from_db()
        self.assertEqual(original.rating, 4)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_unique_pair_allows_other_participants(self):
        """Allow reviews for other businesses and by other customers."""
        self.make_review()
        self.make_review(business=self.other)
        another = self.make_user("another", "customer")
        self.make_review(reviewer=another)
        self.assertEqual(Review.objects.count(), 3)

    def test_database_enforces_uniqueness(self):
        """Enforce the duplicate rule even when bypassing the API service."""
        self.make_review()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(
                    business_user=self.owner,
                    reviewer=self.customer,
                    rating=5,
                    description="Duplicate",
                )
        self.assertEqual(Review.objects.count(), 1)

    def test_unrelated_integrity_errors_are_not_hidden(self):
        """Do not misreport storage failures as duplicate review errors."""
        with patch(
            "reviews_app.services.Review.objects.create",
            side_effect=IntegrityError("simulated failure"),
        ):
            with self.assertRaises(IntegrityError):
                create_review(
                    business_user=self.owner,
                    reviewer=self.customer,
                    rating=4,
                    description="Text",
                )
        self.assertFalse(Review.objects.exists())
