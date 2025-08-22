from django.db import models

from cortanae.generic_utils.models_utils import (
    ActiveInactiveModelMixin,
    BaseModelMixin,
)
from apps.users.models import User

# Create your models here.


class Account(BaseModelMixin, ActiveInactiveModelMixin):
    """model for storing account information
    handles both internal accounts and external accounts
    """

    ACCOUNT_TYPE = [
        ("savings", "Savings"),
        ("checking", "Checking"),
    ]
    user = models.OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="user_accounts",
    )
    account_number = models.CharField(max_length=25, unique=True, null=False)
    account_name = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    account_type = models.CharField(choices=ACCOUNT_TYPE, max_length=30)
    bank_name = models.CharField(
        max_length=255, default="Cortanae Capital Bank"
    )
    account_pin = models.CharField(max_length=255)
