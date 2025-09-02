# apps/common/channels_jwt.py
import urllib.parse
import logging
from typing import Optional

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


def _get_header(headers, name: str) -> Optional[str]:
    """
    Extract a specific HTTP header from ASGI scope['headers'].
    Headers are a list of (key: bytes, value: bytes).
    """
    name_bytes = name.lower().encode()
    for k, v in headers or []:
        if k.lower() == name_bytes:
            return v.decode()
    return None


async def _authenticate_token(raw_token: str):
    """
    Validate JWT and return (user, validated_token) or (AnonymousUser, None).
    """
    if not raw_token:
        return AnonymousUser(), None

    auth = JWTAuthentication()
    try:
        validated_token = auth.get_validated_token(raw_token)
        user = await database_sync_to_async(auth.get_user)(validated_token)
        return user, validated_token
    except Exception as exc:
        logger.warning(f"[WS][JWT] Token validation failed: {exc}")
        return AnonymousUser(), None


class JWTAuthMiddleware:
    """
    ASGI middleware for Channels to authenticate WebSocket connections via JWT.

    Priority:
      1) Query string:  ws://.../path/?token=<JWT>
      2) Authorization: "Bearer <JWT>"  (if client supports custom headers)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Default to anonymous
        scope["user"] = AnonymousUser()

        # Parse query params
        query_string = scope.get("query_string", b"").decode()
        qs = urllib.parse.parse_qs(query_string)
        token = (qs.get("token") or [None])[0]

        # Fallback: Authorization header ("Bearer <token>")
        if not token:
            auth_header = _get_header(scope.get("headers"), "authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1].strip()

        user, _ = await _authenticate_token(token)
        scope["user"] = user

        if getattr(user, "is_authenticated", False):
            logger.debug(f"[WS][JWT] Authenticated user id={user.id}")
        else:
            logger.debug("[WS][JWT] Anonymous connection")

        return await self.app(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Convenience factory to wrap URLRouter (or any ASGI app) with JWT auth middleware.
    """
    return JWTAuthMiddleware(inner)
