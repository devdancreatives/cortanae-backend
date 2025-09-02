from email.mime import text
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
import json


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            user = self.scope.get("user")
            # 🔒 Require authenticated user (JWT or session via middleware)
            if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
                print("[WS][AUTH] Anonymous connection rejected")
                await self.close(code=4401)  # 4401: Unauthorized (custom)
                return
            
            self.group_name = f"user_{user.id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            
        except Exception as e:
            print(f"[WS] connect error: {e}")
            await self.close()
        

    async def send_notification(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "notification_type": event["notification_type"],
                    "title": event.get("title"),
                    "id": event.get("id"),
                }
            )
        )

    async def receive(self, text_data=None, bytes_data=None):
        print(text_data)

    async def disconnect(self, code):
        return await self.channel_layer.group_discard(
            self.group_name, self.channel_layer
        )
