from enum import unique
from cortanae.generic_utils.models_utils import BaseModelMixin
from django.contrib.auth.models import AbstractUser
from django.db import models
from django_countries.fields import CountryField


class User(AbstractUser, BaseModelMixin):
    phone_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    country = CountryField()

    @property
    def full_name(self):
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_full_name(self):
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()
