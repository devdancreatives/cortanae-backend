# # cortanae/asgi.py
# import os, django

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cortanae.settings")
# django.setup()

# from django.conf import settings
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from channels.security.websocket import AllowedHostsOriginValidator
# import apps.chat.routing
# import apps.notifications.routing as notification_routing

# django_asgi_app = get_asgi_application()

# ws = AuthMiddlewareStack(
#     URLRouter(
#         apps.chat.routing.websocket_urlpatterns
#         + notification_routing.webosocket_urlpatterns
#     )
# )
# # if getattr(settings, "ENVIRONMENT", "local") != "local":
# #     ws = AllowedHostsOriginValidator(ws)  # only enforce in prod

# application = ProtocolTypeRouter(
#     {
#         "http": django_asgi_app,
#         "websocket": ws,
#     }
# )


# cortanae/asgi.py
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cortanae.settings")
django.setup()
print("[ASGI] Django setup complete.")

from django.conf import settings
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

import apps.chat.routing as chat_routing
import apps.notifications.routing as notification_routing
from cortanae.channels_jwt import JWTAuthMiddlewareStack


django_asgi_app = get_asgi_application()
print("[ASGI] HTTP application ready.")


ws_urlpatterns = []
ws_urlpatterns += getattr(chat_routing, "websocket_urlpatterns", [])
ws_urlpatterns += getattr(notification_routing, "websocket_urlpatterns", [])

print(f"[ASGI] Loaded {len(ws_urlpatterns)} WebSocket route(s).")

ws_app = JWTAuthMiddlewareStack(URLRouter(ws_urlpatterns))

# Enforce allowed hosts outside local/dev
if getattr(settings, "ENVIRONMENT", "local") != "local":
    ws_app = AllowedHostsOriginValidator(ws_app)
    print("[ASGI] AllowedHostsOriginValidator enabled.")

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": ws_app,
    }
)

print("[ASGI] ProtocolTypeRouter configured.")
