from django.db import models
from cortanae.generic_utils.models_utils import (
    ActiveInactiveModelMixin,
    BaseModelMixin,
)


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

    ssn = models.CharField(max_length=20)
    account_type = models.CharField(
        choices=ACCOUNT_TYPE, max_length=25, null=False, blank=False
    )
    income_range = models.CharField(max_length=35)
    address = models.TextField()
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    country = models.CharField(max_length=100)
    nationality = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=255)
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
    user = models.OneToOneField(
        "users.User", on_delete=models.CASCADE, related_name="kyc_profile"
    )

    def __str__(self):
        return f"Kyc for {self.user.first_name} {self.user.last_name}"
