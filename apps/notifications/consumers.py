from email.mime import text
from channels.generic.websocket import AsyncWebsocketConsumer
import json


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.group_name = f"user_{self.scope['user'].id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

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
