from django.db import models
from django.contrib.auth.hashers import (
    make_password,
    check_password,
    identify_hasher,
)

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
    checking_acc_number = models.CharField(
        max_length=25, unique=True, null=False
    )
    savings_acc_number = models.CharField(
        max_length=25, unique=True, null=False
    )
    account_name = models.CharField(max_length=255)
    checking_balance = models.DecimalField(
        "Checking Balance", max_digits=12, decimal_places=2, default=0
    )
    savings_balance = models.DecimalField(
        "Saving Balance", max_digits=12, decimal_places=2, default=0
    )
    bank_name = models.CharField(
        max_length=255, default="Cortanae Capital Bank"
    )
    account_pin = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.account_name} - {self.checking_acc_number} / {self.savings_acc_number}"

    def save(self, *args, **kwargs):
        if self.account_pin:
            try:
                # If account_pin is already hashed, skip rehash
                identify_hasher(self.account_pin)
            except Exception:
                # account_pin is raw → hash it
                self.account_pin = make_password(self.account_pin)

        super().save(*args, **kwargs)

    def check_account_pin(self, raw_pin: str) -> bool:
        """Verify a raw PIN against the stored hash."""
        ok = check_password(raw_pin, self.account_pin or "")
        print(ok)
        if not ok:
            return False
        print(f"[PIN] Verify • account={self.pk} •")
        return True
