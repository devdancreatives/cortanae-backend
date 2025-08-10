from enum import unique
from django.db import models
from cortanae.generic_utils.models_utils import (
    BaseModelMixin,
)
from django_countries.fields import CountryField


class KYC(BaseModelMixin):
    ACCOUNT_TYPE = [("savings", "Savings"), ("checking", "Checking")]
    EMPLOYMENT_TYPE = [
        ("unemployed", "Unemployed"),
        ("employed", "Employed"),
    ]
    DOCUMENT_TYPE = [
        ("passport", "Int. Passport"),
        ("national_id", "National Id"),
        ("driver_license", "Driver license"),
    ]

    STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.OneToOneField(
        "users.User", on_delete=models.CASCADE, related_name="kyc_profile"
    )
    ssn = models.CharField(max_length=50)
    account_type = models.CharField(
        choices=ACCOUNT_TYPE, max_length=25, null=False, blank=False
    )
    full_name = models.CharField(max_length=255)
    email = models.CharField(unique=True, max_length=255)
    phone_number = models.CharField(max_length=20, unique=True, null=True)
    income_range = models.CharField(max_length=35)
    address = models.TextField()
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    country = CountryField()
    nationality = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    title = models.CharField(max_length=30)
    gender = models.CharField(max_length=25)
    zip_code = models.CharField(max_length=10)
    date_of_birth = models.DateField(blank=True)

    # Next of kin information
    kin_name = models.CharField(max_length=255)
    kin_address = models.CharField(max_length=255)
    relationship = models.CharField(max_length=50)
    kin_date_of_birth = models.DateField()

    # document
    document_type = models.CharField(choices=DOCUMENT_TYPE, max_length=50)
    doument_front = models.CharField(max_length=255)
    domument_back = models.CharField(max_length=255)
    passport_image = models.CharField(max_length=255)
    error_message = models.TextField(
        help_text="Kyc approval status message", blank=True
    )
    status = models.CharField(choices=STATUS, max_length=255)

    def __str__(self):
        return f"Kyc for {self.user.first_name} {self.user.last_name}"
 