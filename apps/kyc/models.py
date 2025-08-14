from django.db import models
from django.conf import settings
from django_countries.fields import CountryField
from cloudinary.models import CloudinaryField
from cortanae.generic_utils.models_utils import BaseModelMixin
from apps.users.models import User


class KYC(BaseModelMixin):
    ACCOUNT_TYPE = [("savings", "Savings"), ("checking", "Checking")]
    EMPLOYMENT_TYPE = [("unemployed", "Unemployed"), ("employed", "Employed")]
    DOCUMENT_TYPE = [
        ("passport", "Int. Passport"),
        ("national_id", "National Id"),
        ("driver_license", "Driver license"),
    ]
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="kyc_profile")

    ssn = models.CharField(max_length=50)
    account_type = models.CharField(choices=ACCOUNT_TYPE, max_length=25)
    full_name = models.CharField(max_length=255)
    email = models.CharField(unique=True, max_length=255)

    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)

    income_range = models.CharField(max_length=35)
    address = models.TextField()
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    country = CountryField()
    nationality = models.CharField(max_length=100)
    title = models.CharField(max_length=30)
    gender = models.CharField(max_length=25)
    zip_code = models.CharField(max_length=10)
    date_of_birth = models.DateField(null=True, blank=True)

    # Next of kin
    kin_name = models.CharField(max_length=255)
    kin_address = models.CharField(max_length=255)
    relationship = models.CharField(max_length=50)
    kin_date_of_birth = models.DateField(null=True, blank=True)

    # Document meta
    document_type = models.CharField(choices=DOCUMENT_TYPE, max_length=50)

    # ✅ Cloudinary-managed images (renamed + fixed typos)
    document_front = CloudinaryField("document_front", null=True, blank=True)
    document_back = CloudinaryField("document_back", null=True, blank=True)
    passport_image = CloudinaryField("passport_image", null=True, blank=True)

    error_message = models.TextField(help_text="KYC approval status message", blank=True, default="")
    status = models.CharField(choices=STATUS, max_length=20, default="pending")

    def __str__(self):
        return f"KYC • {self.user_id} • {self.status}"

    def save(self, *args, **kwargs):
        print(f"[KYC] Saving profile for user_id={self.user_id} status={self.status}")
        super().save(*args, **kwargs)
