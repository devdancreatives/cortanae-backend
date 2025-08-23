from uuid import uuid4
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from cloudinary.models import CloudinaryField

from cortanae.generic_utils.models_utils import BaseModelMixin
from apps.accounts.models import Account

from decimal import Decimal

class TxCategory(models.TextChoices):
    DEPOSIT = "deposit", "Deposit"
    TRANSFER_INT = "transfer_internal", "Transfer (Internal)"
    TRANSFER_EXT = "transfer_external", "Transfer (External Wire)"
    WITHDRAWAL = "withdrawal", "Withdrawal"


class TxStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCESSFUL = "successful", "Successful"
    CANCELLED = "cancelled", "Cancelled"
    FAILED = "failed", "Failed"


class TxMethod(models.TextChoices):
    WIRE = "wire_transfer", "Wire Transfer"
    BANK = "bank_transfer", "Bank Transfer"
    INTERNAL = "internal", "Internal"


class Transaction(BaseModelMixin):
    """
    Lean single-table design:
    - Use category to distinguish flows (deposit / transfer-int / transfer-ext / withdrawal)
    - Optional source/destination for each flow
    - Minimal meta goes to TransactionMeta
    """

    ACCOUNT_TYPE = [
        ("savings", "Savings"),
        ("checking", "Checking"),
    ]
    
    reference = models.CharField(max_length=50, unique=True, blank=True)
    category = models.CharField(max_length=24, choices=TxCategory.choices)
    method = models.CharField(max_length=24, choices=TxMethod.choices)
    account_type = models.CharField("Transaction Account Type", choices=ACCOUNT_TYPE, max_length=30, blank=True, null=True)

    # Internal participants (optional depending on flow)
    source_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tx_source",
    )
    destination_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tx_destination",
    )

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    fee_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )

    status = models.CharField(
        max_length=16, choices=TxStatus.choices, default=TxStatus.PENDING
    )
    error_message = models.TextField(null=True, blank=True)

    # Who initiated the transaction (user/admin)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="initiated_txs",
    )

    # Optional idempotency to prevent duplicates from FE
    idempotency_key = models.CharField(
        max_length=100, null=True, blank=True, unique=True
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reference"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self):
        return f"{self.reference} • {self.category} • {self.amount} {self.currency} • {self.status}"

    @property
    def net_amount(self) -> Decimal:
        return self.amount - (self.fee_amount or Decimal("0.00"))

    def clean(self):
        if self.amount <= 0:
            raise ValidationError(
                {"amount": "Amount must be greater than zero."}
            )

        if self.category == TxCategory.DEPOSIT:
            if not self.destination_account:
                raise ValidationError(
                    "Deposit requires a destination_account."
                )
            if self.method not in (
                TxMethod.WIRE,
                TxMethod.BANK,
            ):
                raise ValidationError("Invalid method for deposit.")

        if self.category == TxCategory.TRANSFER_INT:
            if not self.source_account or not self.destination_account:
                raise ValidationError(
                    "Internal transfer requires source and destination accounts."
                )
            if self.source_account_id == self.destination_account_id:
                raise ValidationError(
                    "Source and destination cannot be the same."
                )
            if self.method != TxMethod.INTERNAL:
                raise ValidationError(
                    "Internal transfer must use method 'internal'."
                )

        if self.category in (TxCategory.TRANSFER_EXT, TxCategory.WITHDRAWAL):
            if not self.source_account:
                raise ValidationError(
                    "External transfer/withdrawal requires source_account."
                )
            if self.method not in (
                TxMethod.WIRE,
                TxMethod.BANK,
            ):
                raise ValidationError(
                    "Invalid method for external transfer/withdrawal."
                )

class TransactionMeta(BaseModelMixin):
    """Optional extra fields per flow without bloating Transaction."""

    transaction = models.OneToOneField(
        Transaction, on_delete=models.CASCADE, related_name="meta"
    )
    # External beneficiary (wire/bank)
    beneficiary_name = models.CharField(max_length=255, null=True, blank=True)
    beneficiary_account_number = models.CharField(
        max_length=255, null=True, blank=True
    )
    beneficiary_bank_name = models.CharField(
        max_length=255, null=True, blank=True
    )
    banking_routing_number = models.CharField(
        max_length=255, null=True, blank=True
    )
    bank_swift_code = models.CharField(max_length=255, null=True, blank=True)
    recipient_address = models.TextField(null=True, blank=True)


    # ✅ Cloudinary-managed assets (replaces FileField)
    payment_proof = CloudinaryField(
        "payment_proofs",
        null=True,
        blank=True,
        folder="transactions/payment_proofs",
    )
    receipt = CloudinaryField(
        "receipts", null=True, blank=True, folder="transactions/receipts"
    )
    
    class Meta:
        verbose_name = "Transaction Details"
        verbose_name_plural = "Transaction Details"  # ✅ Fix plural

    def __str__(self):
        return f"Meta • {self.transaction.reference}"


class TransactionHistory(BaseModelMixin):
    # ACTION_CHOICES = [
    #     ("created", "Created"),
    #     ("status_change", "Status Change"),
    #     ("details_update", "Details Update"),
    # ]
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="history"
    )
    metadata = models.JSONField(default=dict, blank=True)
    note = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Transaction History"
        verbose_name_plural = "Transaction Histories"  # ✅ Fix plural


    def __str__(self):
        return f"{self.transaction.reference}"
