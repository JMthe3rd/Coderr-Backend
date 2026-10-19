"""Exercise multipart offer creation and validated image updates."""

import json
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from .helpers import OfferTestCase, offer_payload


def image_upload():
    """Produce a small valid PNG for actual image validation."""
    stream = BytesIO()
    Image.new("RGB", (4, 4), "blue").save(stream, format="PNG")
    return SimpleUploadedFile("offer.png", stream.getvalue(), "image/png")


class OfferImageTests(OfferTestCase):
    """Verify the combined multipart image and nested JSON contract."""

    def setUp(self):
        """Isolate uploads from the development media directory."""
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.enterContext(self.settings(MEDIA_ROOT=directory.name))

    def test_multipart_creation_with_nested_packages(self):
        """Create an offer using a real image and a JSON details field."""
        data = offer_payload()
        data["details"] = json.dumps(data["details"])
        data["image"] = image_upload()
        response = self.client.post(self.url, data, format="multipart")
        self.assertEqual(response.status_code, 201)
        self.assertIn("/media/offers/", response.data["image"])
        self.assertEqual(len(response.data["details"]), 3)

    def test_patch_image_and_clear_reference(self):
        """Replace an image with multipart data and clear it with JSON null."""
        offer = self.make_offer()
        url = f"/api/offers/{offer.pk}/"
        response = self.client.patch(url, {"image": image_upload()})
        self.assertEqual(response.status_code, 200)
        self.assertIn("/media/offers/", response.data["image"])
        response = self.client.patch(url, {"image": None}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["image"])

    def test_invalid_json_and_fake_images(self):
        """Return 400 for malformed multipart details and fake images."""
        data = offer_payload()
        data["details"] = "invalid JSON"
        self.assertEqual(self.client.post(self.url, data).status_code, 400)
        offer = self.make_offer()
        url = f"/api/offers/{offer.pk}/"
        upload = SimpleUploadedFile("fake.png", b"not an image")
        self.assertEqual(
            self.client.patch(url, {"image": upload}).status_code, 400
        )

    def test_non_list_features(self):
        """Reject a string where a list of feature strings is required."""
        data = offer_payload()
        data["details"][0]["features"] = "Design"
        self.assertEqual(self.post_offer(data).status_code, 400)
