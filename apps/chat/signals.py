from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.notifications.service.notification_service import (
    send_push_notification,
)
from .models import Chat
import logging
db_logger = logging.getLogger("db")

User = get_user_model()


@receiver(post_save, sender=Chat)
def send_signal_on_new_message(sender, created, instance, **kwargs):
    if created and instance.receiver:
        db_logger.info(
            f"[WS][SIGNAL] New message from {instance.sender} to {instance.receiver}"
        )
        send_push_notification(
            title = instance.sender.username,
            body=instance.text,
            single_user= True,
            user= instance.receiver
        )
        db_logger.info(f"[WS][SIGNAL] Push notification sent to {instance.receiver}")
