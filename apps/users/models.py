from enum import unique
from cortanae.generic_utils.models_utils import BaseModelMixin
from django.contrib.auth.models import AbstractUser
from django.db import models
from django_countries.fields import CountryField


class User(AbstractUser, BaseModelMixin):
    phone_number = models.CharField(max_length=20, unique=True, null=True)
    is_verified = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    country = CountryField()
    verification_token = models.CharField(max_length=500, null=True)
    is_deleted = models.BooleanField(default=False)

    @property
    def full_name(self):
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_full_name(self):
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]


class TokenValidator(BaseModelMixin):
    TOKEN_TYPE = [
        ("verify_account", "Verify account"),
        ("reset_password", "Reset password"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.CharField(max_length=100)
    token_type = models.CharField(choices=TOKEN_TYPE, max_length=25)
    is_active = models.BooleanField(default=True)
