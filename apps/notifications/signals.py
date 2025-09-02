from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification


@receiver(post_save, sender=Notification)
def send_notification_ws(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        group_name = f"user_{instance.user.id}"
        print("Sending notification to group:", group_name)

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",  # matches the consumer method
                "message": instance.content,  # customize payload
                "title": instance.title,
                "id": instance.id,
                "notification_type": instance.title,
            },
        )
