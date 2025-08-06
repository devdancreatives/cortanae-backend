from django.db import models
from accounts.models import Account
from cortanae.generic_utils.models_utils import BaseModelMixin

# Create your models here.


class Transactions(BaseModelMixin):
    TRANSACTION_STATUS = [
        ("pending", "Pending"),
        ("reversed", "Reversed"),
        ("cancelled", "Cancelled"),
    ]
    DEPOSIT_TYPE = [("bitcoin", "Bitcoin"), ("wire transfer", "Wire transfer")]
    TRANSACTION_FLOW = [("inflow", "Inflow"), ("outflow", "Outflow")]
    TRANSACTION_TYPE = [
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
        ("transfer", "Transfer"),
        ("refund", "Refund"),
    ]

    user = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name="sent_transactions",
        null=True,
    )
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    status = models.CharField(choices=TRANSACTION_STATUS, max_length=15)
    description = models.TextField(null=True, blank=True)
    reference = models.CharField(max_length=50, null=False, blank=False)
    deposit_type = models.CharField(choices=DEPOSIT_TYPE)
    transaction_flow = models.CharField(choices=TRANSACTION_FLOW)
    receipt = models.CharField(null=True, max_length=255)
    recipient = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name="received_transactions",
        null=True,
    )
    transaction_type = models.CharField(
        choices=TRANSACTION_TYPE, max_length=30
    )
    session_id = models.CharField(max_length=255)

    class Meta:
        ordering = ["-created_at"]
