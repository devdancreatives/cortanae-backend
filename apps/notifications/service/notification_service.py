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
from apps.users.models import User

from cortanae.generic_utils.mail_send import mail_service

User = get_user_model()

import logging
db_logger = logging.getLogger("db")

def send_notification(user, content, title, type, mail_options=None):
    Notification.objects.create(
        user=user, title=title, content=content, type=type
    )

    if user.email_notifications and mail_options:
        mail_service.mail_send(**mail_options)


def send_push_notification(
    title: str, body: str, single_user: bool, user: User | None
):
    db_logger.info(f"[WS][PUSH] Sending push notification to {user}")
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
                db_logger.info(f"[WS][PUSH] FCM response: {result}")
                if result.get("name"):
                    continue
            except FCMServerError as e:
                db_logger.error(f"[WS][PUSH] FCM server error for token {token}")
                raise RuntimeError(
                    "An error occured that the FCM server could not process"
                ) from e
            except AuthenticationError as e:
                db_logger.warning(f"[WS][PUSH] Authentication error for token {token}")
                raise PermissionError(
                    "User Firebase account cannot be authenticated at the present time"
                ) from e
            except InvalidDataError as e:
                db_logger.warning(f"[WS][PUSH] Invalid data for token {token}")
                raise ValueError(
                    "Data passed to method is not of the right structure"
                ) from e
            except FCMSenderIdMismatchError as e:
                db_logger.warning(f"[WS][PUSH] Sender ID mismatch for token {token}")
                raise PermissionError(
                    "Credentials of sender not the same as authenticated sender on FCM"
                ) from e
            except FCMNotRegisteredError as e:
                db_logger.warning(f"[WS][PUSH] Deleting invalid token {token}")
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
