from django.utils import timezone
from rest_framework import serializers
from .models import KYC


class KYCSerializer(serializers.ModelSerializer):
    """Read serializer for KYC."""
    class Meta:
        model = KYC
        fields = [
            "id",
            "user",
            "ssn",
            "account_type",
            "full_name",
            "email",
            "phone_number",
            "income_range",
            "address",
            "state",
            "city",
            "country",
            "nationality",
            "title",
            "gender",
            "zip_code",
            "date_of_birth",
            "kin_name",
            "kin_address",
            "relationship",
            "kin_date_of_birth",
            "document_type",
            "document_front",
            "document_back",
            "passport_image",
            "error_message",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "error_message", "created_at", "updated_at"]


class KYCWriteSerializer(serializers.ModelSerializer):
    """Create/Update serializer for the owner. User is always request.user."""
    class Meta:
        model = KYC
        fields = [
            "ssn",
            "account_type",
            "full_name",
            "email",
            "phone_number",
            "income_range",
            "address",
            "state",
            "city",
            "country",
            "nationality",
            "title",
            "gender",
            "zip_code",
            "date_of_birth",
            "kin_name",
            "kin_address",
            "relationship",
            "kin_date_of_birth",
            "document_type",
            "document_front",
            "document_back",
            "passport_image",
        ]

    def validate(self, attrs):
        print("[KYCWriteSerializer.validate] Validating KYC payload…")
        # Optional: normalize email/phone
        if email := attrs.get("email"):
            attrs["email"] = email.strip().lower()
        if phone := attrs.get("phone_number"):
            attrs["phone_number"] = phone.strip()
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        print(f"[KYCWriteSerializer.create] user_id={user.id}")

        if KYC.objects.filter(user=user).exists():
            raise serializers.ValidationError("KYC profile already exists for this user.")

        instance = KYC.objects.create(user=user, **validated_data)
        print(f"[KYCWriteSerializer.create] KYC created id={instance.id} at {timezone.now()}")
        return instance

    def update(self, instance, validated_data):
        print(f"[KYCWriteSerializer.update] Updating KYC id={instance.id}")
        # When user edits KYC, keep status pending; clear error_message
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.status = "pending"
        instance.error_message = ""
        instance.save()
        print(f"[KYCWriteSerializer.update] KYC saved id={instance.id} status={instance.status}")
        return instance


class KYCStatusUpdateSerializer(serializers.ModelSerializer):
    """Admin-only status updates with optional error_message."""
    class Meta:
        model = KYC
        fields = ["status", "error_message"]

    def validate_status(self, value):
        if value not in dict(KYC.STATUS):
            raise serializers.ValidationError("Invalid status.")
        return value