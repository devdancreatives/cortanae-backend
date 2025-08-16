from django.forms import ValidationError
from django.db import transaction
from django.views.generic import detail
from rest_framework import serializers

from apps.accounts.models import Account

from .models import (
    Transaction,
    TransactionHistory,
    TransactionMeta,
    TxCategory,
    TxMethod,
    TxStatus,
)


class DepositSerializer(serializers.ModelSerializer):
    wallet_address = serializers.CharField(required=False, blank=True)
    beneficiary_account_number = serializers.CharField(
        required=False, blank=True
    )
    category = serializers.CharField(required=True)
    amount = serializers.DecimalField(
        required=True, max_digits=14, decimal_places=2
    )
    payment_proof = serializers.ImageField(required=True)
    method = serializers.CharField(required=True)

    class Meta:
        model = Transaction
        fields = [
            "method",
            "amount",
            "payment_proof",
            "category",
            "wallet_address",
            "beneficiary_account_number",
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError(
                {
                    "details": "Amount to be deposited cannot be zero or less than zero"
                }
            )
        return value

    def validate_category(self, value):
        if value != TxCategory.DEPOSIT:
            raise ValidationError(
                {
                    "details": "Category must be deposit, for deposit transactions"
                }
            )
        return value

    def validate_method(self, value):
        if value not in [TxMethod.BITCOIN, TxMethod.WIRE, TxMethod.WIRE]:
            raise ValidationError({"detail": "Deposit method not allowed"})
        return value

    def validate(self, attrs):
        method = attrs.get("method")
        wallet_address = attrs.get("wallet_address", "")
        beneficiary_account_number = attrs.get("beneficiary_account_number")

        if method == TxMethod.BITCOIN:
            if not wallet_address:
                raise ValidationError(
                    {"details": "Wallet address not provided"}
                )
            attrs["beneficiary_account_number"] = ""
        elif method in [TxMethod.WIRE, TxMethod.BANK]:
            if not beneficiary_account_number:
                raise ValidationError(
                    {
                        "details": "Beneficiary account number is required for bank/wire transfers."
                    }
                )
            attrs["wallet_address"] = ""

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        if not hasattr(user, "user_accounts"):
            raise ValidationError(
                {"error": "User does not have an account with the bank"}
            )
        user_account = user.user_accounts
        payment_proof = validated_data.pop("payment_proof")
        wallet_address = validated_data.pop("wallet_address")
        transaction = Transaction.objects.create(
            **validated_data,
            destination_account=user_account,
            initiated_by=user,
        )
        account_number = validated_data.get("beneficiary_account_number", None)
        TransactionMeta.objects.create(
            transaction=transaction,
            wallet_address=wallet_address,
            payment_proof=payment_proof,
            beneficiary_account_number=account_number,
        )
        return transaction


class TransferSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    category = serializers.CharField(required=True)
    method = serializers.CharField(required=True)
    description = serializers.CharField(required=False)
    beneficiary_account_number = serializers.IntegerField()
    beneficiary_bank_name = serializers.CharField(required=True)
    beneficiary_name = serializers.CharField(required=True)

    class Meta:
        model = Transaction

    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError(
                {"detail": "Amount cannot be lesser or equal to zero"}
            )
        return value

    def validate_method(self, value):
        valid_methods = [TxMethod.BANK, TxMethod.INTERNAL, TxMethod.WIRE]
        if value not in valid_methods:
            raise ValidationError(
                {
                    "details": f"Method must be one of {", ".join(valid_methods)}"
                }
            )
        return value

    def validate_category(self, value):
        valid_categories = [TxCategory.TRANSFER_EXT, TxCategory.TRANSFER_INT]
        if value not in valid_categories:
            raise ValidationError({"details": "Transfers only allowed"})
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        category = attrs.get("category")
        method = attrs.get("method")

        if category == TxCategory.TRANSFER_INT and method != TxMethod.INTERNAL:
            raise ValidationError(
                {"details": 'Internal transfers must use "internal" method'}
            )

        # External transfers cannot use internal method
        if category == TxCategory.TRANSFER_EXT and method == TxMethod.INTERNAL:
            raise ValidationError(
                {"details": 'External transfers cannot use "internal" method'}
            )

        # External transfers require beneficiary details
        if category == TxCategory.TRANSFER_EXT:
            if not attrs.get("beneficiary_name"):
                raise ValidationError(
                    {
                        "details": "Beneficiary name is required for external transfers"
                    }
                )
            if method in [TxMethod.BANK, TxMethod.WIRE] and not attrs.get(
                "beneficiary_bank_name"
            ):
                raise ValidationError(
                    {
                        "details": "Bank name is required for bank/wire transfers"
                    }
                )
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user

        if not hasattr(user, "user_accounts"):
            raise ValidationError({"details": "User does not have an account"})

        user_account = user.user_accounts

        category = validated_data.get("category")
        if category == TxCategory.TRANSFER_INT:
            return self.handle_internal_transfer(validated_data, user_account)
        elif category == TxCategory.TRANSFER_EXT:
            return self.handle_external_transfer(validated_data, user_account)
        else:
            raise ValidationError({"details": "Invalid transfer category"})

    def handle_internal_transfer(self, validated_data, user_account):
        """function to handle internal transfers"""
        beneficiary_account_number = validated_data.pop(
            "beneficiary_account_number"
        )
        destination_account = self.check_internal_account(
            beneficiary_account_number
        )
        if not destination_account:
            raise ValidationError(
                {
                    "details": "Beneficiary does not have an account with the bank"
                }
            )
        if user_account.id == destination_account.id:
            raise ValidationError(
                {"details": "Cannot transfer to your own account"}
            )
        amount = validated_data.get("amount")
        with transaction.atomic():
            user_account = Account.objects.select_for_update().get(
                pk=user_account.pk
            )
            destination_account = Account.objects.select_for_update().get(
                pk=destination_account.pk
            )

            if user_account.balance < amount:
                raise ValidationError({"details": "Insufficient funds"})
            # debit sender
            user_account.balance -= amount
            destination_account.balance += amount
            user_account.save()
            destination_account.save()
            transaction_instance = Transaction.objects.create(
                **validated_data,
                destination_account=destination_account,
                status=TxStatus.COMPLETED,
                initiated_by=self.context["request"].user,
            )
            TransactionMeta.objects.create(transaction=transaction_instance)

    def check_internal_account(self, account_number: int) -> Account | None:
        try:
            user_account = Account.objects.get(account_number=account_number)
            return user_account
        except Account.DoesNotExist:
            return None

    def handle_external_transfer(self, validated_data, user_account):
        """Handle external transfers (wire/bank)"""

        # Separate meta data
        meta_data = {
            "beneficiary_account_number": validated_data.pop(
                "beneficiary_account_number"
            ),
            "beneficiary_name": validated_data.pop("beneficiary_name"),
            "beneficiary_bank_name": validated_data.pop(
                "beneficiary_bank_name"
            ),
        }

        # just to confirm that the user is not trying to be smart
        destination_account = self.check_internal_account(
            meta_data["beneficiary_account_number"]
        )
        if user_account == destination_account:
            raise ValidationError(
                {"details": "Transfers to the same account is not allowed"}
            )
        try:
            with transaction.atomic():
                # For external transfers, we typically don't debit immediately
                # They go through approval/processing workflow

                # Create transaction record
                transaction_instance = Transaction.objects.create(
                    **validated_data,
                    source_account=user_account,
                    initiated_by=self.context["request"].user,
                    status=TxStatus.PENDING,  # just to be explicit
                )

                # Create transaction meta
                TransactionMeta.objects.create(
                    transaction=transaction_instance, **meta_data
                )

                return transaction_instance

        except Exception as e:
            raise ValidationError({"detail": f"Transfer failed: {str(e)}"})


class TransactionHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = TransactionHistory
        depth = 1
        fields = "__all__"


class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transaction
        depth = 1
        fields = "__all__"
