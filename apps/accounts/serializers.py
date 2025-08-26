from django.db import models
from django.forms import ValidationError
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, Serializer
from .models import Account
import random


class AccountPinChangeSerializer(ModelSerializer):
    account_pin = serializers.CharField(required=True)
    new_account_pin = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = Account
        fields = ["account_pin", "new_account_pin"]

    def validate_account_pin(self, value):
        user = self.context["request"].user.user_accounts
        if not user.check_account_pin(value):
            raise ValidationError({"details": "Incorrect pin"})
        return value

    def validate_new_account_pin(self, value):
        user_account = self.context["request"].user.user_accounts
        if user_account.check_account_pin(value):
            raise ValidationError(
                {"detail": "Old account pin is the same as new pin"}
            )
        return value

    def update(self, instance, validated_data):
        new_pin = validated_data.pop("new_account_pin")
        instance.account_pin = new_pin
        instance.save()
        return instance


class AccountCreateSerializer(ModelSerializer):
    account_pin = serializers.CharField(required=True)

    class Meta:
        model = Account
        fields = ["account_number", "account_name"]

    def create(self, validated_data):

        return super().create(**validated_data)


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account  # import from your app's models
        fields = (
            "id",
            "account_name",
            "bank_name",
            "checking_balance",
            "savings_balance",
            "checking_acc_number",
            "savings_acc_number",
        )
