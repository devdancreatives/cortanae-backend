from django.urls import path
from .apis import (
    FCMDeviceCreateView,
    GetAllUserNotifications,
    GetSingleNotification,
    MarkNotificationRead,
    MarkAllNotificationsRead,
)

urlpatterns = [
    path("", GetAllUserNotifications.as_view(), name="all-notifications"),
    path(
        "<uuid:pk>/",
        GetSingleNotification.as_view(),
        name="single-notification",
    ),
    path(
        "<uuid:pk>/mark-read/",
        MarkNotificationRead.as_view(),
        name="mark-notification-read",
    ),
    path(
        "mark-all-read/",
        MarkAllNotificationsRead.as_view(),
        name="mark-all-notifications-read",
    ),
    path("fcm-devices/", FCMDeviceCreateView.as_view(), name="fcm devices"),
]

