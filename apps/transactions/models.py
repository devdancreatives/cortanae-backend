from django.db import models
from django.conf import settings
from accounts.models import Account
from cortanae.generic_utils.models_utils import BaseModelMixin


class Transaction(BaseModelMixin):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("reversed", "Reversed"),
        ("cancelled", "Cancelled"),
    ]
    FLOW_CHOICES = [
        ("inflow", "Inflow"),
        ("outflow", "Outflow"),
    ]
    TYPE_CHOICES = [
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
        ("transfer", "Transfer"),
        ("refund", "Refund"),
    ]
    METHOD_CHOICES = [
        ("bitcoin", "Bitcoin"),
        ("wire_transfer", "Wire Transfer"),
        ("bank_transfer", "Bank Transfer"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_status = self.status  # Store status at object load

    user = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name="initiated_transactions",
        null=True,
    )
    recipient = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name="received_transactions",
        null=True,
        blank=True,
    )

    amount = models.DecimalField(decimal_places=2, max_digits=12)
    currency = models.CharField(max_length=10, default="USD")  # e.g., BTC, USD

    status = models.CharField(choices=STATUS_CHOICES, max_length=15)
    flow = models.CharField(choices=FLOW_CHOICES, max_length=10)
    transaction_type = models.CharField(choices=TYPE_CHOICES, max_length=30)
    transaction_method = models.CharField(
        choices=METHOD_CHOICES, max_length=30
    )

    reference = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    receipt = models.FileField(
        upload_to="transactions/receipts/", null=True, blank=True
    )
    payment_proof = models.FileField(
        upload_to="transactions/payment_proofs/", null=True, blank=True
    )
    session_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        self._changed_by = kwargs.pop(
            "changed_by", None
        )  # Who made the change
        super().save(*args, **kwargs)


class TransactionMeta(models.Model):
    """Extra details for specific transaction types (domestic wire, BTC tx hash, etc.)"""

    transaction = models.OneToOneField(
        Transaction, on_delete=models.CASCADE, related_name="meta"
    )
    # Wire transfer fields
    recipient_full_name = models.CharField(
        max_length=255, null=True, blank=True
    )
    recipient_account_number = models.CharField(
        max_length=255, null=True, blank=True
    )
    recipient_bank_name = models.CharField(
        max_length=255, null=True, blank=True
    )

    # Bitcoin-specific fields
    blockchain_tx_hash = models.CharField(
        max_length=255, null=True, blank=True
    )
    wallet_address = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Meta for {self.transaction.reference}"


class TransactionHistory(BaseModelMixin):
    ACTION_CHOICES = [
        ("created", "Created"),
        ("status_change", "Status Change"),
        ("details_update", "Details Update"),
        ("reversed", "Reversed"),
        ("cancelled", "Cancelled"),
    ]

    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.CASCADE,
        related_name="history",
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    previous_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20, null=True, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # or Account model
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaction_changes",
    )
    metadata = models.JSONField(
        default=dict, blank=True
    )  # extra info about the change
    note = models.TextField(null=True, blank=True)  # optional remarks

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"History for {self.transaction.reference} - {self.action}"
