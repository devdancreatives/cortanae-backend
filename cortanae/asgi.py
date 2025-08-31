# Django 4.2/5.x — ASGI entrypoint
import os
import django

# ✅ Ensure settings are configured BEFORE importing anything that touches models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cortanae.settings")
django.setup()
print("[DEBUG] ASGI: DJANGO_SETTINGS_MODULE set and django.setup() completed.")

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

# Import AFTER setup() so consumers/models don’t crash
from apps.chat import routing as chat_routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(chat_routing.websocket_urlpatterns)
        )
    ),
})
