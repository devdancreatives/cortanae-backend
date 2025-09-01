# cortanae/asgi.py
import os

# 1) Configure settings FIRST
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cortanae.settings")

# 2) Setup Django before importing anything that touches models/apps
import django
django.setup()

# 3) Now safe to import Channels pieces and your routing/consumers
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import apps.chat.routing  # now safe

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(apps.chat.routing.websocket_urlpatterns)
        )
    ),
})
