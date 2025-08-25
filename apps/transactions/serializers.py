from django.forms import ValidationError
import datetime
from django.db import transaction
from django.views.generic import detail
from rest_framework import serializers
from django.db.models import Q

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
    category = serializers.CharField(required=True)
    amount = serializers.DecimalField(
        required=True, max_digits=14, decimal_places=2
    )
    payment_proof = serializers.ImageField(required=True, write_only=True)
    method = serializers.CharField(required=True)
    account_type = serializers.CharField(required=False)

    class Meta:
        model = Transaction
        fields = [
            "method",
            "amount",
            "payment_proof",
            "category",
            "account_type",
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
        if value not in [TxMethod.WIRE, TxMethod.BANK]:
            raise ValidationError({"detail": "Deposit method not allowed"})
        return value

    def validate(self, attrs):
        method = attrs.get("method")
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        if not hasattr(user, "user_accounts"):
            raise ValidationError(
                {"error": "User does not have an account on the platform"}
            )
        user_account = user.user_accounts
        payment_proof = validated_data.pop("payment_proof")
        transaction = Transaction.objects.create(
            **validated_data,
            destination_account=user_account,
            initiated_by=user,
        )
        # account_number = validated_data.get("beneficiary_account_number", None)
        TransactionMeta.objects.create(
            transaction=transaction,
            payment_proof=payment_proof,
        )
        return transaction

    def to_representation(self, instance):
        """Include payment_proof in output"""
        data = super().to_representation(instance)
        data["payment_proof"] = (
            instance.meta.payment_proof.url
            if instance.meta and instance.meta.payment_proof
            else None
        )
        return data


class TransactionMetaSerializer(serializers.ModelSerializer):
    # transaction = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        # fields = "__all__"
        exclude = ["transaction"]
        model = TransactionMeta


class TransferSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    category = serializers.CharField(required=True)
    method = serializers.CharField(required=True)
    meta = TransactionMetaSerializer()
    account_type = serializers.CharField(required=True)
    account_pin = serializers.CharField(write_only=True, required=True)

    class Meta:
        depth = 1
        model = Transaction
        fields = [
            "amount",
            "category",
            "method",
            "account_pin",
            "account_type",
            "meta",
        ]

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
                    "details": f"Method must be one of {', '.join(valid_methods)}"
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
        meta_data = attrs.get("meta") or {}

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
            if not meta_data.get("beneficiary_name"):
                raise ValidationError(
                    {
                        "details": "Beneficiary name is required for external transfers"
                    }
                )
            if method in [TxMethod.BANK, TxMethod.WIRE] and not meta_data.get(
                "beneficiary_bank_name"
            ):
                raise ValidationError(
                    {
                        "details": "Bank name is required for bank/wire transfers"
                    }
                )
        return attrs

    def create(self, validated_data):
        meta_data = validated_data.pop("meta", None)
        user = self.context["request"].user

        if not hasattr(user, "user_accounts"):
            raise ValidationError({"details": "User does not have an account"})

        user_account = user.user_accounts

        category = validated_data.get("category")
        if category == TxCategory.TRANSFER_INT:
            return self.handle_internal_transfer(
                validated_data, meta_data, user_account
            )
        elif category == TxCategory.TRANSFER_EXT:
            return self.handle_external_transfer(
                validated_data, meta_data, user_account
            )
        else:
            raise ValidationError({"details": "Invalid transfer category"})

    def handle_internal_transfer(
        self, validated_data, meta_data, user_account
    ):
        """function to handle internal transfers"""
        beneficiary_account_number = meta_data.get(
            "beneficiary_account_number"
        )
        print("==> ", beneficiary_account_number)

        destination_acc_type, destination_account = (
            self.check_internal_account(beneficiary_account_number)
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
        account_type = validated_data.get("account_type")

        with transaction.atomic():
            user_account = Account.objects.select_for_update().get(
                pk=user_account.pk
            )
            destination_account = Account.objects.select_for_update().get(
                pk=destination_account.pk
            )

            if (
                account_type == "savings"
                and user_account.savings_balance < amount
            ):
                raise ValidationError({"details": "Insufficient funds"})

            if (
                account_type == "checkings"
                and user_account.checking_balance < amount
            ):
                raise ValidationError({"details": "Insufficient funds"})

            # debit sender
            if account_type == "savings":
                user_account.savings_balance -= amount
                if destination_acc_type == "checking":
                    destination_account.checking_balance += amount
                else:
                    destination_account.savings_balance += amount

            elif account_type == "checking":
                user_account.checking_balance -= amount
                if destination_acc_type == "checking":
                    destination_account.checking_balance += amount
                else:
                    destination_account.savings_balance += amount
            else:
                raise ValidationError({"details": "Invalid account type"})

            user_account.save()
            destination_account.save()

            account_pin = validated_data.pop("account_pin")
            description = validated_data.pop("description", "")

            if not user_account.check_account_pin(account_pin):
                raise ValidationError({"details": "Invalid account pin"})

            transaction_instance = Transaction.objects.create(
                **validated_data,
                destination_account=destination_account,
                status=TxStatus.SUCCESSFUL,
                initiated_by=self.context["request"].user,
            )

            TransactionMeta.objects.create(
                transaction=transaction_instance, **(meta_data or {})
            )
            return transaction_instance

    def check_internal_account(self, account_number: str):
        """
        Fast, safe lookup for an internal account number across checking/savings.
        """
        normalized = (
            str(account_number) if account_number is not None else ""
        ).strip()
        if not normalized:
            print("[AccountLookup] Empty account_number provided.")
            return None

        account = (
            Account.objects.only(
                "id",
                "checking_acc_number",
                "savings_acc_number",
                "account_name",
                "user_id",
            )
            .filter(
                Q(checking_acc_number=normalized)
                | Q(savings_acc_number=normalized)
            )
            .first()
        )

        if not account:
            print(f"[AccountLookup] Not found for '{normalized}'.")
            return None

        acct_type = (
            "checking"
            if account.checking_acc_number == normalized
            else "savings"
        )
        print(
            f"[AccountLookup] Found {acct_type} account • id={account.id} • user_id={account.user_id}"
        )
        return acct_type, account

    def handle_external_transfer(
        self, validated_data, meta_data, user_account
    ):
        """Handle external transfers (wire/bank)"""
        acct_type, destination_account = self.check_internal_account(
            meta_data.get("beneficiary_account_number")
        )

        if user_account == destination_account:
            raise ValidationError(
                {"details": "Transfers to the same account is not allowed"}
            )
        try:
            with transaction.atomic():
                transaction_instance = Transaction.objects.create(
                    **validated_data,
                    source_account=user_account,
                    initiated_by=self.context["request"].user,
                    status=TxStatus.PENDING,
                )

                TransactionMeta.objects.create(
                    transaction=transaction_instance, **(meta_data or {})
                )
                return transaction_instance

        except Exception as e:
            raise ValidationError({"detail": f"Transfer failed: {str(e)}"})


class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transaction
        depth = 1
        fields = "__all__"


class TransactionHistorySerializer(serializers.ModelSerializer):
    # transaction = TransactionSerializer(read_only=True)

    class Meta:
        model = TransactionHistory
        depth = 1
        fields = "__all__"
