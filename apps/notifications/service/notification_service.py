from apps.notifications.models import Notification

from cortanae.generic_utils.mail_send import mail_service


def send_notification(user, content, title, type, mail_options=None):
    Notification.objects.create(
        user=user, title=title, content=content, type=type
    )

    if user.email_notifications or mail_options:
        mail_service.mail_send(**mail_options)
