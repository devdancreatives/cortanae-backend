from contextvars import Token
from django.db.models.signals import post_save
from django.dispatch import receiver

from cortanae.generic_utils.account_verification import verification_mail
from .models import TokenValidator, User


@receiver(post_save, sender=User)
def send_account_verification_mail(sender, instance, created, **kwargs):
    if created:
        print("The signal has been triggered")
        verification_mail(instance, "verify_account")
