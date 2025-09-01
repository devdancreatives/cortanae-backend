from rest_framework import serializers
from apps.chat.models import Room, Chat
from apps.users.serializers import UserSerializer


class RoomSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    room_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Room
        fields = (
            "room_id",
            "sender",
            "receiver",
            # add the rest of your Room model fields explicitly
            "created_at",
            "updated_at",
            # e.g. "name", "last_message", etc.
        )

    def get_room_id(self, obj):
        return obj.id


class ChatSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    reciever = UserSerializer(read_only=True)

    class Meta:
        model = Chat
        fields = "__all__"
