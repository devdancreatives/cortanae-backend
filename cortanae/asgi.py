# cortanae/asgi.py
import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cortanae.settings")
django.setup()

from django.conf import settings
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import apps.chat.routing
import apps.notifications.routing as notification_routing

django_asgi_app = get_asgi_application()

ws = AuthMiddlewareStack(
    URLRouter(
        apps.chat.routing.websocket_urlpatterns
        + notification_routing.webosocket_urlpatterns
    )
)
# if getattr(settings, "ENVIRONMENT", "local") != "local":
#     ws = AllowedHostsOriginValidator(ws)  # only enforce in prod

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": ws,
    }
)
