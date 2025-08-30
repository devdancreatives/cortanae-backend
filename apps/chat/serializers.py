from rest_framework import serializers
from apps.chat.models import Room, Chat
from apps.users.serializers import UserSerializer


class RoomSerializer(serializers.ModelSerializer):
    sender = UserSerializer()
    reciever = UserSerializer()

    class Meta:
        model = Room
        fields = "__all__"


class ChatSerializer(serializers.ModelSerializer):
    sender = UserSerializer()
    reciever = UserSerializer()

    class Meta:
        model = Chat
        fields = "__all__"
