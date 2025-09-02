from django.urls import re_path
from .consumers import NotificationConsumer

webosocket_urlpatterns = [
    re_path("ws/notifications/$", NotificationConsumer.as_asgi())
]
