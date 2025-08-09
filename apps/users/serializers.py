from django.utils.ipv6 import ValidationError
from rest_framework import serializers
from cortanae.generic_utils.account_verification import verification_mail
from cortanae.generic_utils.token_verification import verify_token
from .models import User, TokenValidator
from rest_framework_simplejwt.authentication import AuthUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token
from typing import Union


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    username = serializers.CharField(required=True)
    country = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = [
            "email",
            "country",
            "password",
            "first_name",
            "last_name",
            "username",
            "phone_number",
        ]

    def validate(self, attrs):
        email = attrs.get("email", None)
        username = attrs.get("username", None)
        errors = {}
        if User.objects.filter(email__iexact=email).exists():
            errors["email"] = "Email already in use"
        if User.objects.filter(username__iexact=username).exists():
            errors["username"] = "Username already in use"
        if errors:
            raise ValidationError(errors)

        return attrs

    def create(self, validated_data):
        email = validated_data.pop("email").lower()
        validated_data["email"] = email
        user = User.objects.create_user(**validated_data)
        return user


class PasswordResetSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=True)
    token = serializers.CharField(required=True)

    class Meta:
        model = TokenValidator
        fields = ["password", "token"]

    def validate(self, attrs):
        user_token = attrs.get("token")
        if not user_token:
            raise ValidationError({"detail", "Token not provided"})

        token_instance = TokenValidator.objects.filter(
            token=user_token, token_type="reset_password"
        ).first()
        if not token_instance:
            raise ValidationError({"detail": "No token"})
        is_valid, user, reason = verify_token(token_instance)
        if not is_valid:
            raise ValidationError({"detail": reason})

        attrs["user_instance"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data.get("user_instance")
        password = self.validated_data.get("password")
        user.set_password(password)
        user.save()
        return user


class PasswordResetRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenValidator
        fields = ["email"]

    def validate(self, attrs):
        email = attrs.get("email")
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ValidationError({"detail": "User does not exist"})
        attrs["user"] = user
        return attrs

    def create(self, validated_data):
        user = validated_data.get("user")
        verification_mail(user, "reset_password")
        return user


class VerifyAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenValidator
        fields = ["__all__"]

    def validate(self, attrs):
        token = attrs.get("token").strip()
        if not token:
            raise ValidationError({"detail": "No token provided"})

        token_instance = TokenValidator.objects.filter(token=token).exists()
        if not token_instance:
            return ValidationError({"detail": "Invalid token"})

        # verify token
        user = User.objects.filter(email=token_instance.email).first()
        if not user:
            return ValidationError({"detail": "No user with email"})
        is_valid, user, reason = verify_token(token_instance)
        if not is_valid:
            raise ValidationError({"detail", reason})
        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.is_verified = True
        user.save()

        return user


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["__all__"]


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct")
        return value

    def validate_new_password(self, value):
        # You can add custom password validation here (length, complexity)
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters"
            )
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save()
        return user


class UserLoginSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        email = attrs.get("email")
        if email and isinstance(email, str):
            attrs["email"] = email.lower()

        # Retrieve user here to perform status checks before token generation
        user = User.objects.filter(email=attrs["email"]).first()
        if user:
            if user.is_deleted:
                raise serializers.ValidationError(
                    {"detail": "User account has been deleted"}
                )
            if not user.is_verified:
                verification_mail(user, "verify_account")
                raise serializers.ValidationError(
                    {
                        "detail": "Please confirm your profile before you can login"
                    }
                )
        if not user:
            raise ValidationError({"detail": "Invalid login credentials"})
        return super().validate(attrs)

    @classmethod
    def get_token(cls, user: AuthUser) -> Token:
        token = super().get_token(user)
        token["full_name"] = user.full_name
        token["email"] = user.email
        token["account"] = getattr(user, "user_accounts", None)
        return token
