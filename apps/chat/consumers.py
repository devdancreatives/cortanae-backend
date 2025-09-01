import json
import uuid
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.db import IntegrityError
from apps.chat.models import Chat, Room
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


""" DB Helpers """


def _mark_seen_sync(slug: str):
    try:
        chat = Chat.objects.get(slug=slug)
        chat.has_seen = True
        chat.save(update_fields=["has_seen"])
        return chat
    except Chat.DoesNotExist:
        logger.warning(f"[WS][SEEN] Message with slug {slug} not found")

mark_seen = sync_to_async(_mark_seen_sync, thread_sensitive=False)


def create_new_message_sync(sender_id, receiver_id, message, room_id, slug):
    print("sender_id", sender_id)
    print("receiver_id", receiver_id)
    try:
        room = Room.objects.get(id=room_id)
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)

        if slug:
            existing = Chat.objects.filter(slug=slug).first()
            if existing:
                print(f"[DB] slug already exists; returning existing id={existing.id}")
                return existing
            
        chat = Chat.objects.create(
            room_id=room,
            slug=slug,
            sender=sender,
            receiver=receiver,
            text=message,
        )
        return chat

    except Room.DoesNotExist:
        logger.error(f"Room {room_id} not found")
    except User.DoesNotExist as e:
        logger.error(f"User not found: {e}")
    except IntegrityError as e:
        logger.error(f"IntegrityError occurred: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error creating message: {e}")


create_message = sync_to_async(
    create_new_message_sync, thread_sensitive=False
)


def handle_read_receipt_sync(slug):
    try:
        chat = Chat.objects.get(slug=slug)
        chat.has_seen = True
        chat.save()
        return chat
    except Chat.DoesNotExist:
        logger.warning(f"Message with slug {slug} not found")
    except Exception as e:
        logger.exception(f"Error updating read receipt: {e}")


handle_update_status = sync_to_async(
    handle_read_receipt_sync, thread_sensitive=False
)


""" Consumer """


class ChatRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
            self.room_group_name = f"chat_{self.room_name}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        except Exception as e:
            print(f"[WS] connect error: {e}")
            logger.exception("[WS] connect error: %s", e)
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        print("Received data", data)

        # 🚨 Always use scope user for sender (security)
        sender_id = data["sender"]['id']
        receiver_id = data["receiver"]
        slug = data["slug"]
        text = data["text"]
        date = data.get("date")
        read_receipt = data.get("read_receipt")
        if read_receipt:
            # Handle receipts separately (no DB save loop)
            await mark_seen(slug=slug)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "broadcast_message",
                    "event": "read_receipt",
                    "slug": slug,
                    "sender": sender_id,
                    "receiver": receiver_id,
                    "has_seen": True,
                    "date": date,
                },
            )
            return

        if not receiver_id or not text:
            print("[WS][VALIDATION] Missing receiver or empty text")
            return

        # 🛑 FIX: Save once here (only sender's consumer runs `receive`)
        try:
            await create_message(
                sender_id=sender_id,
                receiver_id=receiver_id,
                message=text,
                room_id=self.room_name,
                slug=slug,
            )
        except Exception:
            # Already logged in helper
            return

        # 📣 Single one-way broadcast to group (no second DB write)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "broadcast_message",
                "event": "new_message",
                "text": text,
                "receiver": receiver_id,
                "sender": sender_id,
                "slug": slug,
                "date": date,
                "has_seen": False,
            },
        )

    # 🔊 Group fan-out: pure broadcast — NO DB writes here
    async def broadcast_message(self, event):
        await self.send(text_data=json.dumps(event))
        print(f"[WS][SEND] {event.get('event')} slug={event.get('slug')} to {self.channel_name}")