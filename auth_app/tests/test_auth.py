"""Verify the public account contract and rejected requests."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from auth_app.models import UserProfile


class AuthenticationTests(TestCase):
    """Exercise account creation, password storage and token login."""

    def setUp(self):
        """Prepare valid registration data and an API client."""
        self.client = APIClient()
        self.payload = {
            "username": "coderr_user",
            "email": "user@example.com",
            "password": "Secure-Coderr-729!",
            "repeated_password": "Secure-Coderr-729!",
            "type": "customer",
        }

    def register(self, **changes):
        """Submit a registration with optional field overrides."""
        return self.client.post(
            "/api/registration/", self.payload | changes, format="json"
        )

    def assert_account_response(self, response, user):
        """Check the response contract and stored token."""
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Token.objects.get(user=user).key, response.data["token"]
        )
        self.assertEqual(response.data["user_id"], user.pk)
        self.assertEqual(
            set(response.data), {"token", "username", "email", "user_id"}
        )

    def test_register_both_roles(self):
        """Create each role with a hashed password and matching token."""
        for role in ["customer", "business"]:
            with self.subTest(role=role):
                response = self.register(username=role, type=role)
                user = get_user_model().objects.get(username=role)
                self.assertTrue(user.check_password(self.payload["password"]))
                self.assertEqual(user.profile.type, role)
                self.assert_account_response(response, user)

    def test_invalid_registration_creates_no_accounts(self):
        """Reject invalid roles, credentials and malformed fields."""
        changes = [
            {"type": "admin"},
            {"email": "invalid"},
            {"username": ""},
            {"repeated_password": "different"},
            {"email": ""},
            {"password": "123", "repeated_password": "123"},
        ]
        for change in changes:
            with self.subTest(change=change):
                self.assertEqual(self.register(**change).status_code, 400)
        self.assert_no_accounts()

    def assert_no_accounts(self):
        """Ensure invalid registration leaves no partial records."""
        for model in [get_user_model(), UserProfile, Token]:
            self.assertEqual(model.objects.count(), 0)

    def test_duplicate_username(self):
        """Reject an existing username without creating an extra profile."""
        self.register()
        self.assertEqual(self.register().status_code, 400)
        self.assertEqual(UserProfile.objects.count(), 1)

    def test_login_reuses_registration_token(self):
        """Return the documented account data for valid credentials."""
        registration = self.register()
        response = self.client.post(
            "/api/login/",
            {
                "username": self.payload["username"],
                "password": self.payload["password"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, registration.data)

    def assert_login_rejected(self, username, password):
        """Submit credentials and require the documented error status."""
        response = self.client.post(
            "/api/login/",
            {
                "username": username,
                "password": password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_wrong_and_unknown_login(self):
        """Reject incorrect passwords and unknown users."""
        self.register()
        self.assert_login_rejected(self.payload["username"], "wrong")
        self.assert_login_rejected("unknown", "wrong")

    def test_inactive_login(self):
        """Reject an inactive account even with its correct password."""
        self.register()
        user = get_user_model().objects.get()
        user.is_active = False
        user.save()
        self.assert_login_rejected(user.username, self.payload["password"])

    def test_missing_credentials(self):
        """Require request fields for both public endpoints."""
        for route in ["registration", "login"]:
            response = self.client.post(f"/api/{route}/", {}, format="json")
            self.assertEqual(response.status_code, 400)
