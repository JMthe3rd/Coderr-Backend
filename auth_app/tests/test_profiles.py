"""Verify profile contracts, ownership and real image uploads."""

import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from auth_app.models import UserProfile


def make_user(username, role):
    """Create a test account and role profile."""
    user = get_user_model().objects.create_user(username=username)
    UserProfile.objects.create(user=user, type=role)
    return user


def image_upload(image_format="PNG"):
    """Generate a real image rather than trusting file extensions."""
    stream = BytesIO()
    Image.new("RGB", (4, 4), "red").save(stream, format=image_format)
    return SimpleUploadedFile(
        "avatar." + image_format.lower(), stream.getvalue()
    )


class ProfileTests(TestCase):
    """Check detail, update and list behavior with isolated media storage."""

    def setUp(self):
        """Prepare distinct user and profile IDs and token authentication."""
        get_user_model().objects.create_user(username="without_profile")
        self.owner = make_user("business", "business")
        self.other = make_user("customer", "customer")
        self.client = APIClient()
        token = Token.objects.create(user=self.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.url = f"/api/profile/{self.owner.pk}/"
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.enterContext(self.settings(MEDIA_ROOT=directory.name))

    def test_all_routes_require_authentication(self):
        """Return 401 for anonymous reads and profile edits."""
        self.client.credentials()
        for url in [
            self.url,
            "/api/profiles/business/",
            "/api/profiles/customer/",
        ]:
            self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.patch(self.url, {}).status_code, 401)

    def test_profile_uses_user_id_and_empty_strings(self):
        """Use the account identifier and never null optional text fields."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"], self.owner.pk)
        self.assertEqual(response.data["username"], self.owner.username)
        fields = "first_name last_name location tel description working_hours"
        for field in fields.split():
            self.assertEqual(response.data[field], "")
        self.assertIsNone(response.data["file"])

    def test_read_other_profile_and_missing_profile(self):
        """Allow authenticated reads and return 404 for missing profiles."""
        url = f"/api/profile/{self.other.pk}/"
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(
            self.client.get("/api/profile/99999/").status_code, 404
        )

    def test_update_user_and_profile_fields(self):
        """Persist nested user data and preserve unspecified profile fields."""
        data = {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "location": "Vienna",
        }
        response = self.client.patch(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.email, "ada@example.com")
        self.assertEqual(self.owner.first_name, "Ada")
        self.assertEqual(self.owner.profile.location, "Vienna")

    def test_forbidden_foreign_update(self):
        """Block editing another user's profile, including staff accounts."""
        self.owner.is_staff = True
        self.owner.save()
        url = f"/api/profile/{self.other.pk}/"
        response = self.client.patch(url, {"location": "Changed"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.other.profile.location, "")

    def test_identity_and_role_are_immutable(self):
        """Ignore attempts to change ownership, username or role."""
        data = {"user": self.other.pk, "type": "customer", "username": "new"}
        response = self.client.patch(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.profile.type, "business")
        self.assertEqual(self.owner.username, "business")

    def test_invalid_updates_do_not_partially_save(self):
        """Reject invalid email, null text and excessive field length."""
        for data in [
            {"email": "invalid"},
            {"location": None},
            {"tel": "x" * 51},
            {"first_name": "x" * 151},
        ]:
            response = self.client.patch(
                self.url, data | {"description": "Changed"}, format="json"
            )
            self.assertEqual(response.status_code, 400)
        self.owner.profile.refresh_from_db()
        self.assertEqual(self.owner.profile.description, "")

    def test_role_lists_have_distinct_contracts(self):
        """Separate roles and omit private fields from public lists."""
        for role, user in [("business", self.owner), ("customer", self.other)]:
            response = self.client.get(f"/api/profiles/{role}/")
            self.assertEqual(response.status_code, 200)
            self.assertIsInstance(response.data, list)
            self.assertEqual(
                [item["user"] for item in response.data], [user.pk]
            )
            self.assertNotIn("email", response.data[0])
            self.assertNotIn("created_at", response.data[0])
            self.assertEqual(
                "uploaded_at" in response.data[0], role == "customer"
            )

    def test_upload_and_remove_image(self):
        """Save validated images, record upload time and support removal."""
        response = self.client.patch(self.url, {"file": image_upload()})
        self.assertEqual(response.status_code, 200)
        self.assertIn("/media/profiles/", response.data["file"])
        self.owner.profile.refresh_from_db()
        self.assertIsNotNone(self.owner.profile.uploaded_at)
        response = self.client.patch(self.url, {"file": None}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["file"])

    def test_reject_disguised_and_unsupported_images(self):
        """Reject text disguised as PNG and unsupported image formats."""
        uploads = [
            SimpleUploadedFile("fake.png", b"not an image"),
            image_upload("GIF"),
        ]
        for upload in uploads:
            response = self.client.patch(self.url, {"file": upload})
            self.assertEqual(response.status_code, 400)
        self.assertFalse(self.owner.profile.file)

    def test_reject_oversized_image(self):
        """Reject a valid image exceeding the documented upload limit."""
        upload = image_upload()
        upload = SimpleUploadedFile(
            "large.png", upload.read() + b"x" * 5242880
        )
        response = self.client.patch(self.url, {"file": upload})
        self.assertEqual(response.status_code, 400)

    def test_unsupported_methods(self):
        """Do not expose full replacement or profile deletion endpoints."""
        self.assertEqual(self.client.put(self.url, {}).status_code, 405)
        self.assertEqual(self.client.delete(self.url).status_code, 405)
