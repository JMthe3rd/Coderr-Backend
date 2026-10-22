"""Author-only updates and deletion of customer reviews."""

from reviews_app.models import Review

from .helpers import ReviewTestCase


class ReviewManagementTests(ReviewTestCase):
    """Protect reviewer identity and permit only editable content changes."""

    def setUp(self):
        """Create a review owned by the authenticated customer."""
        super().setUp()
        self.review = self.make_review()
        self.url = f"/api/reviews/{self.review.pk}/"

    def test_partial_content_updates(self):
        """Allow independent rating and description changes."""
        created_at = self.review.created_at
        for data in [{"rating": 5}, {"description": "Updated feedback"}]:
            response = self.client.patch(self.url, data, format="json")
            self.assertEqual(response.status_code, 200)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.description, "Updated feedback")
        self.assertEqual(self.review.created_at, created_at)
        self.assertGreater(self.review.updated_at, created_at)

    def test_invalid_and_immutable_update_fields(self):
        """Reject invalid data and attempts to reassign review identities."""
        cases = [
            {},
            {"rating": 6},
            {"description": ""},
            {"rating": 5, "business_user": self.other.pk},
            {"rating": 5, "reviewer": self.other.pk},
            {"rating": 5, "extra": "invalid"},
        ]
        for data in cases:
            response = self.client.patch(self.url, data, format="json")
            self.assertEqual(response.status_code, 400)
        self.assert_review_unchanged()

    def assert_review_unchanged(self):
        """Confirm rejected updates leave rating and target unchanged."""
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)
        self.assertEqual(self.review.business_user, self.owner)

    def test_foreign_writes_including_staff(self):
        """Deny both edit and delete for foreign customers and staff."""
        other_customer = self.make_user("other_customer", "customer")
        self.owner.is_staff = True
        self.owner.save()
        for user, expected in [
            (self.owner, 403),
            (other_customer, 403),
            (None, 401),
        ]:
            self.client.force_authenticate(user)
            self.assert_write_status(expected)
        self.assertTrue(Review.objects.filter(pk=self.review.pk).exists())

    def assert_write_status(self, expected):
        """Check both write methods for the authenticated test account."""
        response = self.client.patch(self.url, {"rating": 1}, format="json")
        self.assertEqual(response.status_code, expected)
        self.assertEqual(self.client.delete(self.url).status_code, expected)

    def test_author_delete_and_recreate(self):
        """Return 204 with no body and permit a fresh review after deletion."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(Review.objects.exists())
        self.url = "/api/reviews/"
        self.assertEqual(self.post_review().status_code, 201)

    def test_missing_resource_and_unsupported_methods(self):
        """Return 404 for missing reviews and 405 for single GET or PUT."""
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.client.put(self.url, {}).status_code, 405)
        self.url = "/api/reviews/99999/"
        self.assert_write_status(404)

    def test_query_filters_do_not_hide_write_targets(self):
        """Apply list filters only to the list rather than write lookups."""
        url = self.url + f"?reviewer_id={self.owner.pk}"
        response = self.client.patch(url, {"rating": 5}, format="json")
        self.assertEqual(response.status_code, 200)
