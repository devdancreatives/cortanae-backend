from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.notifications.service.notification_service import send_notification
from apps.accounts.models import Account
from django.utils import timezone


@receiver(post_save, sender=Account)
def notify_account_changes(sender, instance: Account, created, **kwargs):
    """
    Notify user when an account is created or key details change.
    """
    title = "Account Notification"

    if created:
        content = f"Your account {instance.account_name} has been successfully created."
    else:
        # For updates, you could customize based on which fields changed
        content = f"Your account {instance.account_name} has been updated."

    mail_options = {
        "title": title,
        "content": {
            "user": instance.user,
            "current_year": timezone.now().year,
            "account_name": instance.account_name,
            "checking_balance": instance.checking_balance,
            "savings_balance": instance.savings_balance,
        },
        "recipient": instance.user.email,
        "template": "account_update",  # TODO: create template
        "message": content,
    }

    send_notification(
        user=instance.user,
        content=content,
        title=title,
        type="ACCOUNT",
        mail_options=(
            mail_options if instance.user.email_notifications else None
        ),
    )
