from apps.notifications.models import Notification
from pyfcm.errors import (
    AuthenticationError,
    FCMNotRegisteredError,
    FCMSenderIdMismatchError,
    FCMServerError,
    InvalidDataError,
)
from apps.notifications.models import FCMDevice, Notification
from pyfcm import FCMNotification
from cortanae.generic_utils.mail_send import mail_service
import os
from cortanae.settings import BASE_DIR
from django.contrib.auth import get_user_model
from django.conf import settings

from cortanae.generic_utils.mail_send import mail_service

User = get_user_model()


def send_notification(user, content, title, type, mail_options=None):
    Notification.objects.create(
        user=user, title=title, content=content, type=type
    )

    if user.email_notifications and mail_options:
        mail_service.mail_send(**mail_options)


def send_push_notification(
    title: str, body: str, single_user: bool, user: User | None
):
    push_service = FCMNotification(
        service_account_file=os.path.join(BASE_DIR, settings.SERVICE_FILE)
    )
    tokens = []
    if user:
        tokens = list(
            FCMDevice.objects.filter(user=user).values_list("token", flat=True)
        )
    else:
        tokens = list(FCMDevice.objects.values_list("token", flat=True))
    if tokens and single_user:
        for token in tokens:
            try:
                result = push_service.notify(
                    fcm_token=token,
                    notification_title=title,
                    notification_body=body,
                )
                if result.get("name"):
                    continue
            except FCMServerError as e:
                raise RuntimeError(
                    "An error occured that the FCM server could not process"
                ) from e
            except AuthenticationError as e:
                raise PermissionError(
                    "User Firebase account cannot be authenticated at the present time"
                ) from e
            except InvalidDataError as e:
                raise ValueError(
                    "Data passed to method is not of the right structure"
                ) from e
            except FCMSenderIdMismatchError as e:
                raise PermissionError(
                    "Credentials of sender not the same as authenticated sender on FCM"
                ) from e
            except FCMNotRegisteredError as e:
                FCMDevice.objects.filter(token=token).delete()
                raise ValueError(
                    "Token missing or invalid. Confirm if the device is registered"
                ) from e
    if tokens and not single_user:
        params_list = [
            {
                "registration_id": token,
                "message_title": title,
                "message_body": body,
            }
            for token in tokens
        ]
        return push_service.async_notify_multiple_devices(params_list)
    return "no token"
