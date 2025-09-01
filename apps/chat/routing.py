from django.urls import re_path
from .consumers import ChatRoomConsumer

# UUIDs like 05f06a71-eed6-4acb-9813-01d85eae7502 contain hyphens → use [\w-]+
websocket_urlpatterns = [
    re_path(r"^ws/chat/(?P<room_name>[\w-]+)/$", ChatRoomConsumer.as_asgi()),
]
