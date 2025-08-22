from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Account
import random


class AccountCreateSerializer(ModelSerializer):
    account_type = serializers.CharField(required=True)
    account_pin = serializers.CharField(required=True)

    class Meta:
        models = Account
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
            "account_number",
        )

   
