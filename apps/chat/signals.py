from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.notifications.service.notification_service import (
    send_push_notification,
)
from .models import Chat


User = get_user_model()


@receiver(post_save, sender=Chat)
def send_signal_on_new_message(sender, created, instance, **kwargs):
    if created:
        send_push_notification(
            created.slug, created.text, True, created.receiver
        )
