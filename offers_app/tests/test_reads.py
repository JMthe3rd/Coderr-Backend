"""Public listing, authenticated reads and query parameter behavior."""

from .helpers import OfferTestCase


class OfferReadTests(OfferTestCase):
    """Test read responses and list-only query behavior."""

    def setUp(self):
        """Create listings with distinct owners, prices and delivery times."""
        super().setUp()
        self.offer = self.make_offer()
        self.second = self.make_offer("Logo Design", self.other)
        self.second.details.update(price=300, delivery_time_in_days=2)
        self.detail_url = f"/api/offers/{self.offer.pk}/"
        self.package = self.offer.details.first()
        self.package_url = f"/api/offerdetails/{self.package.pk}/"

    def test_public_paginated_listing(self):
        """Expose aggregate minima, creator summary and links publicly."""
        self.client.force_authenticate(None)
        response = self.client.get(self.url, {"page_size": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertIsNotNone(response.data["next"])
        item = response.data["results"][0]
        self.assertEqual(item["min_price"], 300)
        self.assertEqual(item["min_delivery_time"], 2)
        self.assertEqual(item["user_details"]["username"], "other")
        self.assertTrue(item["details"][0]["url"].startswith("/offerdetails/"))

    def test_authenticated_offer_and_package_reads(self):
        """Return absolute detail links and full package fields."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["min_price"], 100)
        self.assertNotIn("user_details", response.data)
        self.assertEqual(
            response.data["details"][0]["url"],
            "http://testserver" + self.package_url,
        )

    def test_package_read(self):
        """Return full package fields to authenticated readers."""
        response = self.client.get(self.package_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["offer_type"], "basic")
        self.assertEqual(
            response.data["features"], ["Design", "Implementation"]
        )

    def test_private_read_authentication(self):
        """Require tokens for offer detail and package detail reads."""
        self.client.force_authenticate(None)
        for url in [self.detail_url, self.package_url]:
            self.assertEqual(self.client.get(url).status_code, 401)

    def test_missing_resources_and_unsupported_methods(self):
        """Return 404 for absent objects and 405 for unsupported writes."""
        for url in ["/api/offers/99999/", "/api/offerdetails/99999/"]:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.put(self.detail_url, {}).status_code, 405)
        self.assertEqual(
            self.client.patch(self.package_url, {}).status_code, 405
        )

    def test_filters_and_search(self):
        """Filter by creator, minimum price, minimum delivery and text."""
        cases = [
            ({"creator_id": self.owner.pk}, self.offer.pk),
            ({"min_price": 200}, self.second.pk),
            ({"max_delivery_time": 2}, self.second.pk),
            ({"search": "WEBSITE"}, self.offer.pk),
            (
                {"search": "professional", "creator_id": self.owner.pk},
                self.offer.pk,
            ),
        ]
        for query, expected in cases:
            self.assert_query_result(query, expected)

    def assert_query_result(self, query, expected):
        """Assert a filter selects exactly the expected offer."""
        response = self.client.get(self.url, query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [expected]
        )

    def test_ordering_and_pagination(self):
        """Support ascending and descending price plus page navigation."""
        for ordering, expected in [
            ("min_price", self.offer.pk),
            ("-min_price", self.second.pk),
        ]:
            response = self.client.get(
                self.url, {"ordering": ordering, "page_size": 1, "page": 1}
            )
            self.assertEqual(response.data["results"][0]["id"], expected)

    def test_page_navigation(self):
        """Expose pagination links and return 404 past the last page."""
        response = self.client.get(self.url, {"page_size": 1, "page": 2})
        self.assertIsNotNone(response.data["previous"])
        self.assertIsNone(response.data["next"])
        self.assertEqual(
            self.client.get(self.url, {"page": 99}).status_code, 404
        )

    def test_invalid_filter_parameters(self):
        """Return 400 for invalid numeric filters rather than server errors."""
        for query in [
            {"creator_id": "abc"},
            {"min_price": "NaN"},
            {"max_delivery_time": -1},
            {"page_size": 0},
            {"page_size": 101},
            {"page_size": "abc"},
        ]:
            self.assertEqual(self.client.get(self.url, query).status_code, 400)

    def test_filters_do_not_hide_detail_resources(self):
        """Keep object retrieval independent of public-list query filters."""
        response = self.client.get(
            self.detail_url, {"creator_id": self.other.pk}
        )
        self.assertEqual(response.status_code, 200)
