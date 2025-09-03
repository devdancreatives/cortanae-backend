from django.contrib.auth.models import update_last_login
from rest_framework.exceptions import ValidationError
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

import logging

db_logger = logging.getLogger("db")  # for database-related logs


class DepositSerializer(serializers.ModelSerializer):
    category = serializers.CharField(required=True)
    amount = serializers.DecimalField(
        required=True, max_digits=14, decimal_places=2
    )
    payment_proof = serializers.ImageField(required=True, write_only=True)
    payment_proof_2 = serializers.ImageField(required=False, write_only=True)
    method = serializers.CharField(required=True)
    account_type = serializers.CharField(required=False)

    class Meta:
        model = Transaction
        fields = [
            "method",
            "amount",
            "payment_proof",
            "payment_proof_2",
            "category",
            "account_type",
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError(
                {
                    "detail": "Amount to be deposited cannot be zero or less than zero"
                }
            )
        return value

    def validate_category(self, value):
        if value != TxCategory.DEPOSIT:
            raise ValidationError(
                {
                    "detail": "Category must be deposit, for deposit transactions"
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
        # ✅ Robust request/user extraction
        request = self.context.get("request")
        if request is None:
            print(
                "[Deposit][ERROR] Missing DRF request in serializer context."
            )
            raise ValidationError(
                {
                    "detail": "Internal error: request context missing. Contact support."
                }
            )

        user = getattr(request, "user", None)
        if user is None or user.is_anonymous:
            print("[Deposit][ERROR] Anonymous or missing user on request.")
            raise ValidationError({"detail": "Authentication required."})

        # ✅ Ensure user has an account
        user_account = getattr(user, "user_accounts", None)
        if not user_account:
            print(f"[Deposit][ERROR] User {user.id} has no linked account.")
            raise ValidationError(
                {"detail": "User does not have an account on the platform."}
            )

        # ✅ Extract files safely
        payment_proof = validated_data.pop("payment_proof", None)
        payment_proof_2 = validated_data.pop("payment_proof_2", None)
        if not payment_proof:
            raise ValidationError({"detail": "Payment proof is required."})

        print(
            f"[Deposit][CREATE] user={user.id} acct={user_account.id} amount={validated_data.get('amount')}"
        )

        # ✅ Create tx + meta
        tx = Transaction.objects.create(
            **validated_data,
            destination_account=user_account,
            initiated_by=user,
        )
        TransactionMeta.objects.create(
            transaction=tx,
            payment_proof=payment_proof,
            payment_proof_2=payment_proof_2,
        )
        return tx

    def to_representation(self, instance):
        data = super().to_representation(instance)
        meta = getattr(instance, "meta", None)
        data["payment_proof"] = (
            meta.payment_proof.url
            if meta and getattr(meta, "payment_proof", None)
            else None
        )
        return data


class TransactionMetaSerializer(serializers.ModelSerializer):
    beneficiary_account_number = serializers.CharField(
        required=True, trim_whitespace=True
    )
    beneficiary_bank_name = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=True
    )
    beneficiary_name = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=True
    )
    bank_swift_code = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=True
    )
    banking_routing_number = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=True
    )
    recipient_address = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=True
    )
    description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TransactionMeta
        exclude = ["transaction"]

    def validate_beneficiary_account_number(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError(
                "Beneficiary account number is required."
            )
        if not v.isdigit():
            raise serializers.ValidationError(
                "Beneficiary account number must be digits only."
            )
        if not (8 <= len(v) <= 20):
            raise serializers.ValidationError(
                "Beneficiary account number must be 8–20 digits."
            )
        print(f"[Meta.validate] beneficiary_account_number={v}")
        return v


class TransferSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    category = serializers.CharField(required=True)
    method = serializers.CharField(required=True)
    meta = TransactionMetaSerializer()
    account_type = serializers.ChoiceField(
        choices=(("savings", "savings"), ("checking", "checking")),
        required=True,
    )
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

    def validate_account_pin(self, value: str) -> str:
        pin = (value or "").strip()
        if not pin.isdigit():
            raise ValidationError("Account pin must be digits only.")
        # Debug without exposing the PIN
        print(f"[PIN] Provided PIN length={len(pin)} (masked)")
        return pin

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
                {"detail": f"Method must be one of {', '.join(valid_methods)}"}
            )
        return value

    def validate_category(self, value):
        valid_categories = [TxCategory.TRANSFER_EXT, TxCategory.TRANSFER_INT]
        if value not in valid_categories:
            raise ValidationError({"detail": "Transfers only allowed"})
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        category = attrs.get("category")
        method = attrs.get("method")
        meta_data = attrs.get("meta") or {}

        if category == TxCategory.TRANSFER_INT and method != TxMethod.INTERNAL:
            raise ValidationError(
                {"detail": 'Internal transfers must use "internal" method'}
            )

        # External transfers cannot use internal method
        if category == TxCategory.TRANSFER_EXT and method == TxMethod.INTERNAL:
            raise ValidationError(
                {"detail": 'External transfers cannot use "internal" method'}
            )

        # External transfers require beneficiary details
        if category == TxCategory.TRANSFER_EXT:
            if not meta_data.get("beneficiary_name"):
                raise ValidationError(
                    {
                        "detail": "Beneficiary name is required for external transfers"
                    }
                )
            if method in [TxMethod.BANK, TxMethod.WIRE] and not meta_data.get(
                "beneficiary_bank_name"
            ):
                raise ValidationError(
                    {"detail": "Bank name is required for bank/wire transfers"}
                )
        return attrs

    def create(self, validated_data):
        meta_data = validated_data.pop("meta")
        user = self.context["request"].user

        if not hasattr(user, "user_accounts"):
            raise ValidationError({"detail": "User does not have an account"})

        user_account = user.user_accounts

        category = validated_data.get("category")
        if category == TxCategory.TRANSFER_INT:
            return self.handle_internal_transfer(
                validated_data, meta_data, user_account
            )
        elif category == TxCategory.TRANSFER_EXT:
            transaction = self.handle_external_transfer(
                validated_data, meta_data, user_account
            )
            print("Returned transaction", transaction)
            return transaction
        else:
            raise ValidationError({"detail": "Invalid transfer category"})

    def handle_internal_transfer(
        self, validated_data, meta_data, user_account
    ):
        """
        Internal transfers:
        - Safely unpack destination resolution.
        - Provide explicit ValidationError instead of TypeError.
        - Add clear debug logs.
        """
        print(f"[InternalTransfer] meta_data={meta_data}")
        beneficiary_account_number = (meta_data or {}).get(
            "beneficiary_account_number"
        )

        dest_result = self.check_internal_account(beneficiary_account_number)
        dest_type, dest_account = (
            dest_result
            if isinstance(dest_result, (tuple, list))
            else (None, None)
        )

        if not dest_account:
            raise ValidationError(
                {
                    "detail": "Beneficiary does not have an account with the bank."
                }
            )

        if str(user_account.id) == str(dest_account.id):
            raise ValidationError(
                {"detail": "Cannot transfer to your own account."}
            )

        amount = validated_data.get("amount")
        account_type = validated_data.get("account_type")
        print(
            f"[InternalTransfer] amount={amount} account_type={account_type} dest_type={dest_type}"
        )

        if amount is None or amount <= 0:
            raise ValidationError(
                {"detail": "Amount must be greater than zero."}
            )
        if account_type not in ("savings", "checking"):
            raise ValidationError({"detail": "Invalid account type."})

        with transaction.atomic():
            # Lock rows to avoid race conditions
            ua_locked = Account.objects.select_for_update().get(
                pk=user_account.pk
            )
            da_locked = Account.objects.select_for_update().get(
                pk=dest_account.pk
            )

            # ✅ Strict balance check (use '>' so exact-balance-to-zero is allowed if you prefer ≥ change to >=)
            if account_type == "savings" and not (
                ua_locked.savings_balance > amount
            ):
                raise ValidationError(
                    {"detail": "Insufficient funds in savings."}
                )
            if account_type == "checking" and not (
                ua_locked.checking_balance > amount
            ):
                raise ValidationError(
                    {"detail": "Insufficient funds in checking."}
                )

            # Confirm PIN after locks (prevents TOCTOU)
            account_pin = validated_data.pop("account_pin")
            if not ua_locked.check_account_pin(account_pin):
                raise ValidationError({"detail": "Invalid account pin."})

            # 🔁 Move funds
            if account_type == "savings":
                ua_locked.savings_balance -= amount
                if dest_type == "checking":
                    da_locked.checking_balance += amount
                else:
                    da_locked.savings_balance += amount
            else:  # checking
                ua_locked.checking_balance -= amount
                if dest_type == "checking":
                    da_locked.checking_balance += amount
                else:
                    da_locked.savings_balance += amount

            ua_locked.save(
                update_fields=["savings_balance", "checking_balance"]
            )
            da_locked.save(
                update_fields=["savings_balance", "checking_balance"]
            )

            print("At this point in the transaction")
            # Create transaction + meta
            tx = Transaction.objects.create(
                **{
                    k: v
                    for k, v in validated_data.items()
                    if k not in ("account_pin",)
                },
                source_account=ua_locked,
                destination_account=da_locked,
                status=TxStatus.SUCCESSFUL,
                initiated_by=self.context["request"].user,
            )
            TransactionMeta.objects.create(transaction=tx, **(meta_data or {}))

            print(
                f"[InternalTransfer][OK] tx_id={tx.id} src={ua_locked.id} dest={da_locked.id} amt={amount}"
            )
            return tx

    # def handle_internal_transfer(
    #     self, validated_data, meta_data, user_account
    # ):
    #     print("meta_data", meta_data)
    #     """function to handle internal transfers"""
    #     beneficiary_account_number = meta_data.get(
    #         "beneficiary_account_number"
    #     )

    #     destination_acc_type, destination_account = (
    #         self.check_internal_account(beneficiary_account_number)
    #     )

    #     if not destination_account:
    #         raise ValidationError(
    #             {
    #                 "detail": "Beneficiary does not have an account with the bank"
    #             }
    #         )
    #     if user_account.id == destination_account.id:
    #         raise ValidationError(
    #             {"detail": "Cannot transfer to your own account"}
    #         )

    #     amount = validated_data.get("amount")
    #     account_type = validated_data.get("account_type")

    #     with transaction.atomic():
    #         user_account = Account.objects.select_for_update().get(
    #             pk=user_account.pk
    #         )
    #         destination_account = Account.objects.select_for_update().get(
    #             pk=destination_account.pk
    #         )

    #         # ✅ strict ">" checks (return 400, not 500)
    #         if account_type == "savings" and not (
    #             user_account.savings_balance > amount
    #         ):
    #             raise serializers.ValidationError(
    #                 {"detail": "Insufficient funds in savings."}
    #             )
    #         if account_type == "checking" and not (
    #             user_account.checking_balance > amount
    #         ):
    #             raise serializers.ValidationError(
    #                 {"detail": "Insufficient funds in checking."}
    #             )

    #         # debit sender
    #         if account_type == "savings":
    #             user_account.savings_balance -= amount
    #             if destination_acc_type == "checking":
    #                 destination_account.checking_balance += amount
    #             else:
    #                 destination_account.savings_balance += amount

    #         elif account_type == "checking":
    #             user_account.checking_balance -= amount
    #             if destination_acc_type == "checking":
    #                 destination_account.checking_balance += amount
    #             else:
    #                 destination_account.savings_balance += amount
    #         else:
    #             raise ValidationError({"detail": "Invalid account type"})

    #         user_account.save()
    #         destination_account.save()

    #         account_pin = validated_data.pop("account_pin")
    #         # description = validated_data.pop("description", "")

    #         if not user_account.check_account_pin(account_pin):
    #             raise ValidationError({"detail": "Invalid account pin"})

    #         transaction_instance = Transaction.objects.create(
    #             **validated_data,
    #             destination_account=destination_account,
    #             status=TxStatus.SUCCESSFUL,
    #             initiated_by=self.context["request"].user,
    #         )

    #         TransactionMeta.objects.create(
    #             transaction=transaction_instance, **(meta_data or {})
    #         )
    #         return transaction_instance

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

    # def handle_external_transfer(
    #     self, validated_data, meta_data, user_account
    # ):
    #     """Handle external transfers (wire/bank)"""
    #     acct_type, destination_account = self.check_internal_account(
    #         meta_data.get("beneficiary_account_number")
    #     )
    #     account_pin = validated_data.pop("account_pin")

    #     if user_account == destination_account:
    #         raise ValidationError(
    #             {"detail": "Transfers to the same account is not allowed"}
    #         )
    #     try:
    #         with transaction.atomic():
    #             transaction_instance = Transaction.objects.create(
    #                 **validated_data,
    #                 source_account=user_account,
    #                 inite
    #             TransactionMeta.objects.create(
    #                 transaction=transaction_instance, **(meta_data or {})
    #             )
    #             return transaction_instance

    #     except Exception as e:
    #         raise ValidationError({"detail": f"Transfer failed: {str(e)}"})

    # ---- External transfer (DEFENSIVE UNPACK) ----
    def handle_external_transfer(
        self,
        validated_data,
        meta_data,
        user_account,
    ):
        """Handle external transfers (wire/bank)."""
        db_logger.info(f"meta_data {meta_data}")
        ben_acct_raw = (
            meta_data.get("beneficiary_account_number") or ""
        ).strip()
        print(
            f"[ExternalTransfer] beneficiary_account_number='{ben_acct_raw}'"
        )

        # # Defensive: check_internal_account ALWAYS returns a tuple, but guard anyway.
        # result = self.check_internal_account(
        #     ben_acct_raw
        # )  # no need for this since it is an external transfer. instead check for the avvount the user wants to make the payment from
        # if not isinstance(result, (tuple, list)) or len(result) != 2:
        #     print(
        #         "[ExternalTransfer] Fallback: invalid result from check_internal_account -> treating as not found."
        #     )
        #     acct_type, destination_account = (None, None)
        # else:
        #     acct_type, destination_account = result

        # # Prevent same-account transfer if user accidentally provided own number
        # if destination_account and user_account.id == destination_account.id:
        #     raise ValidationError(
        #         {"detail": "Transfers to the same account are not allowed."}
        #     )

        # (Optional) Balance check for external transfer — choose the correct balance field
        account_type = validated_data.pop(
            "account_type", None
        )  # remove non-model field if still present
        amount = validated_data.get("amount")
        if account_type in ("savings", "checking"):
            # lock & validate balance before creating tx
            with transaction.atomic():
                ua_locked = Account.objects.select_for_update().get(
                    pk=user_account.pk
                )
                if account_type == "savings" and not (
                    ua_locked.savings_balance > amount
                ):
                    raise ValidationError(
                        {"detail": "Insufficient funds in savings."}
                    )
                if account_type == "checking" and not (
                    ua_locked.checking_balance > amount
                ):
                    raise ValidationError(
                        {"detail": "Insufficient funds in checking."}
                    )
                # confirm pin
                account_pin = validated_data.pop("account_pin")
                if not ua_locked.check_account_pin(account_pin):
                    raise ValidationError({"detail": "Incorrect PIN"})

                # create transaction (PENDING) and meta
                if account_type == "savings":
                    ua_locked.savings_balance -= amount
                elif account_type == "checking":
                    ua_locked.checking_balance -= amount
                ua_locked.save()
                # FIX: integrity error comes from here
                tx = Transaction.objects.create(
                    **{
                        k: v
                        for k, v in validated_data.items()
                        if k not in ("account_pin",)
                    },  # ensure no leaks
                    source_account=ua_locked,
                    initiated_by=self.context["request"].user,
                    status=TxStatus.PENDING,
                )
                TransactionMeta.objects.create(
                    transaction=tx, **(meta_data or {})
                )
                print(f"[ExternalTransfer][OK] tx_id={tx.id} amount={amount}")
                return tx

        # If no account_type provided (API design), just create pending tx without balance check
        try:
            tx = Transaction.objects.create(
                **{
                    k: v
                    for k, v in validated_data.items()
                    if k not in ("account_pin",)
                },  # ensure no leaks
                source_account=user_account,
                initiated_by=self.context["request"].user,
                status=TxStatus.PENDING,
            )
            TransactionMeta.objects.create(transaction=tx, **(meta_data or {}))
            print(
                f"[ExternalTransfer][OK|NoBalanceCheck] tx_id={tx.id} amount={validated_data.get('amount')}"
            )
            return tx
        except Exception as e:
            print(f"[ExternalTransfer][ERROR] {e}")
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
