from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.notifications.service.notification_service import send_notification
from apps.kyc.models import KYC
from django.utils import timezone


@receiver(post_save, sender=KYC)
def notify_kyc_status_change(sender, instance: KYC, created, **kwargs):
    """
    Notify user when their KYC status changes.
    """
    if created:
        return

    title = "KYC Update"
    content = f"Your KYC status is now: {instance.status.upper()}."

    mail_options = {
        "title": title,
        "content": {
            "user": instance.user,
            "current_year": timezone.now().year,
            "kyc_status": instance.status,
        },
        "recipient": instance.user.email,
        "template": "kyc_status_update",  # no template for this yet
        "message": content,
    }

    send_notification(
        user=instance.user,
        content=content,
        title=title,
        type="KYC",
        mail_options=(
            mail_options if instance.user.email_notifications else None
        ),
    )
