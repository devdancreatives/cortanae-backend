from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from kyc.models import KYC


@receiver(post_save, sender=User)
def create_kyc_for_user(sender, instance, created, **kwargs):
    if created:
        KYC.objects.create(
            email=instance.email,
            full_name=f"{instance.first_name} {instance.last_name}",
        )
