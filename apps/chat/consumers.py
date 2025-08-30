import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(
            text_data=json.dumps({"message": "Welcome to corranae support"})
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.send(
            text_data=json.dumps({"message": f"You said: {data['message']}"})
        )
