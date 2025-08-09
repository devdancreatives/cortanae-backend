from django.db import models

from cortanae.generic_utils.models_utils import (
    ActiveInactiveModelMixin,
    BaseModelMixin,
)
from users.models import User

# Create your models here.


class Account(BaseModelMixin, ActiveInactiveModelMixin):
    """model for storing account information
    handles both internal accounts and external accounts
    """

    ACCOUNT_TYPE = [
        ("savings", "Savings"),
        ("checking", "Checking"),
    ]
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL
    )
    account_number = models.CharField(max_length=25, unique=True)
    account_name = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    account_type = models.CharField(choices=ACCOUNT_TYPE, max_length=30)
    is_internal = models.BooleanField(default=True)
    bank_name = models.CharField(
        max_length=255, default="Cortanae Capital Bank"
    )
    account_pin = models.CharField()
