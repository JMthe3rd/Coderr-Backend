"""Public account registration and login endpoints."""

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import LoginSerializer, RegistrationSerializer


def account_response(user):
    """Return the login token, username, email and user ID."""
    token, _ = Token.objects.get_or_create(user=user)
    return {
        "token": token.key,
        "username": user.username,
        "email": user.email,
        "user_id": user.pk,
    }


class RegistrationView(GenericAPIView):
    """Create customer or business accounts."""

    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Validate and register a new account."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            account_response(serializer.save()), status=status.HTTP_201_CREATED
        )


class LoginView(GenericAPIView):
    """Issue tokens for valid account credentials."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Return the authenticated account and its token."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(account_response(serializer.validated_data["user"]))
