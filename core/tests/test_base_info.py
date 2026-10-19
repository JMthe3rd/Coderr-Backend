"""Public aggregate statistics and their response to review mutations."""

from rest_framework.test import APITestCase

from offers_app.tests.helpers import OfferTestCase
from reviews_app.models import Review
from reviews_app.services import create_review


class EmptyBaseInfoTests(APITestCase):
    """Keep the homepage usable before the first account or review exists."""

    def test_public_empty_statistics(self):
        """Return numeric zero values without authentication."""
        response = self.client.get("/api/base-info/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "review_count": 0,
                "average_rating": 0.0,
                "business_profile_count": 0,
                "offer_count": 0,
            },
        )


class BaseInfoTests(OfferTestCase):
    """Aggregate ratings globally across all business accounts."""

    def setUp(self):
        """Prepare two business accounts and an uneven review distribution."""
        super().setUp()
        self.make_offer()
        for index, (business, rating) in enumerate(
            [(self.owner, 5), (self.owner, 5), (self.other, 4)]
        ):
            self.make_review(index, business, rating)
        self.client.force_authenticate(None)
        self.url = "/api/base-info/"

    def make_review(self, index, business, rating):
        """Create a distinct customer and a review for the chosen business."""
        reviewer = self.make_user(f"reviewer_{index}", "customer")
        create_review(
            business_user=business,
            reviewer=reviewer,
            rating=rating,
            description="Feedback",
        )

    def test_global_rounded_statistics(self):
        """Return the global mean rounded to one decimal and correct counts."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "review_count": 3,
                "average_rating": 4.7,
                "business_profile_count": 2,
                "offer_count": 1,
            },
        )

    def test_statistics_reflect_review_updates_and_deletion(self):
        """Reflect edits and deletion through the review API immediately."""
        review = Review.objects.get(business_user=self.other)
        self.client.force_authenticate(review.reviewer)
        url = f"/api/reviews/{review.pk}/"
        self.assertEqual(
            self.client.patch(url, {"rating": 1}).status_code, 200
        )
        self.assertEqual(self.client.get(self.url).data["average_rating"], 3.7)
        self.assertEqual(self.client.delete(url).status_code, 204)
        response = self.client.get(self.url)
        self.assertEqual(response.data["review_count"], 2)
        self.assertEqual(response.data["average_rating"], 5.0)
