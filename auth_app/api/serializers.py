"""Validate registration and login payloads."""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from auth_app.models import UserProfile
from auth_app.services import register_user


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate account data and matching passwords."""

    repeated_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    type = serializers.ChoiceField(choices=UserProfile.Type.choices)

    class Meta:
        """Explicit registration fields."""

        model = get_user_model()
        fields = ["username", "email", "password", "repeated_password", "type"]
        extra_kwargs = {
            "password": {"write_only": True, "trim_whitespace": False},
            "email": {"required": True, "allow_blank": False},
        }

    def validate(self, attrs):
        """Reject password mismatches and weak passwords."""
        if attrs["password"] != attrs["repeated_password"]:
            raise serializers.ValidationError(
                {"repeated_password": "Passwords do not match."}
            )
        user = get_user_model()(
            username=attrs["username"], email=attrs["email"]
        )
        validate_password(attrs["password"], user=user)
        return attrs

    def create(self, validated_data):
        """Delegate atomic account creation to the account service."""
        return register_user(validated_data)


class LoginSerializer(serializers.Serializer):
    """Authenticate active users by username and password."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        """Resolve credentials without revealing whether an account exists."""
        user = authenticate(request=self.context.get("request"), **attrs)
        if user is None:
            raise serializers.ValidationError("Invalid credentials.")
        return {"user": user}
