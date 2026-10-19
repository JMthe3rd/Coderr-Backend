"""Authenticated review list filtering and ordering."""

from datetime import timedelta

from django.utils import timezone

from reviews_app.models import Review

from .helpers import ReviewTestCase


class ReviewListTests(ReviewTestCase):
    """Read all reviews with optional account filters and sort direction."""

    def setUp(self):
        """Create reviews with distinct authors, targets and ratings."""
        super().setUp()
        self.first = self.make_review(rating=2)
        self.second = self.make_review(business=self.other, rating=5)
        another = self.make_user("another", "customer")
        self.third = self.make_review(reviewer=another, rating=4)

    def test_authenticated_list_without_pagination(self):
        """Allow a business account to read the full review list."""
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 3)

    def test_anonymous_list(self):
        """Require authentication for reading customer reviews."""
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_combined_filters(self):
        """Intersect business and reviewer account filters."""
        query = {
            "business_user_id": self.owner.pk,
            "reviewer_id": self.customer.pk,
        }
        response = self.client.get(self.url, query)
        self.assertEqual([row["id"] for row in response.data], [self.first.pk])
        self.assertEqual(
            self.client.get(self.url, {"business_user_id": 99999}).data, []
        )

    def test_rating_ordering(self):
        """Support ascending and descending rating sort order."""
        for ordering, ratings in [
            ("rating", [2, 4, 5]),
            ("-rating", [5, 4, 2]),
        ]:
            response = self.client.get(self.url, {"ordering": ordering})
            self.assertEqual([row["rating"] for row in response.data], ratings)

    def test_updated_at_ordering(self):
        """Sort by actual update timestamps rather than review IDs."""
        Review.objects.filter(pk=self.first.pk).update(
            updated_at=timezone.now() + timedelta(days=1)
        )
        response = self.client.get(self.url, {"ordering": "-updated_at"})
        self.assertEqual(response.data[0]["id"], self.first.pk)

    def test_invalid_filter_parameters(self):
        """Reject malformed and out-of-range account filter values."""
        for query in [
            {"business_user_id": "invalid"},
            {"reviewer_id": 0},
            {"reviewer_id": -1},
            {"business_user_id": 1.5},
        ]:
            self.assertEqual(self.client.get(self.url, query).status_code, 400)
