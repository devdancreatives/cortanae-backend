from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from apps.chat.models import Room, Chat
from .serializers import RoomSerializer, ChatSerializer
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from apps.users.models import User
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample ,OpenApiResponse


class RoomListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Chat"],
        summary="List my chat rooms",
        description="Returns all rooms where the authenticated user is either the sender or the receiver.",
        responses=OpenApiResponse(
            response=RoomSerializer(many=True),
            examples=[
                OpenApiExample(
                    name="RoomsExample",
                    summary="Typical list response",
                    value=[
                        {
                            "room_id": "e7f9b554-0f0d-3dbd-e8b1-ae226206aa67",
                            "sender": {"id": "e7f9b554-0f0d-3dbd-e8b1-ae226206aa67", "first_name": "Tester", "last_name": ""},
                            "receiver": {"id": "e7f9b554-0f0d-3dbd-e8b1-ae226206aa67", "first_name": "Admin", "last_name": ""},
                            "created": "2025-08-20T13:00:00Z",
                            "updated": "2025-08-28T20:40:12Z"
                        }
                    ]
                )
            ],  
        ),
    )

    def get(self, request, *args, **kwargs):
        all_rooms = Room.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).order_by("-created")

        serializer = RoomSerializer(all_rooms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RoomAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id, receiver_id, *args, **kwargs):
        try:
            room_instance = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        chats = Chat.objects.filter(room_id=room_instance).order_by("date")

        chat_serializer = ChatSerializer(chats, many=True)

        context = {
            "old_chats": chat_serializer.data,
            "my_name": request.user.first_name,
            "receiver_name": get_object_or_404(
                User, pk=receiver_id
            ).first_name,
            "room_id": room_id,
        }
        return Response(context, status=status.HTTP_200_OK)


class GetORCreateChatRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def _admin_qs(self, request):
        """
        Define what 'admin' means for your app.
        Option A: built-in staff flag (most common).
        """
        qs = User.objects.filter(is_active=True, is_staff=True).exclude(id=request.user.id)
        return qs
    
    @extend_schema(
        tags=["Chat"],
        summary="Create or get a room with an admin",
        description="Creates a chat room with the first available admin (or the one you pass via admin_id) and returns it.",
        parameters=[
            OpenApiParameter(name="admin_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: RoomSerializer, 201: RoomSerializer, 404: OpenApiTypes.OBJECT},
    )
    
    def post(self, request, *args, **kwargs):
        admins = self._admin_qs(request)
        receiver = admins.order_by("id").first()
        if not receiver:
            return Response(
                {"detail": "No admin users available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Find existing room between the two users (in either direction)
        room = Room.objects.filter(
            Q(sender=request.user, receiver=receiver) |
            Q(sender=receiver, receiver=request.user)
        ).first()

        if not room:
            room = Room.objects.create(sender=request.user, receiver=receiver)

        serializer = RoomSerializer(room, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)



class UpdateHasSeenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id, receiver_id):
        try:
            try:
                room_instance = Room.objects.get(id=room_id)
            except Room.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

            channel_layer = get_channel_layer()
            room_group_name = "chat_%s" % room_id

            # Your logic to validate the room and receiver goes here
            chats = Chat.objects.filter(
                room_id=room_instance, has_seen=False
            ).order_by("-date")
            receiver_chats = chats.filter(
                Q(sender=receiver_id) | Q(receiver=receiver_id)
            )
            print("receiver_chats", receiver_chats)
            for chat in receiver_chats:
                message = {
                    "type": "chatroom_message",
                    "text": chat.text,
                    "receiver": str(chat.receiver.id),
                    "date": chat.date.isoformat(),
                    "has_seen": chat.has_seen,
                    "sender": str(chat.sender.id),
                    "slug": chat.slug,
                    "read_receipt": "read_receipt",
                }
                chat.has_seen = True  # Update 'has_seen' as needed
                chat.save()
                # Send message to the WebSocket consumer
                async_to_sync(channel_layer.group_send)(
                    room_group_name, message
                )

            return Response(
                {"detail": "Read receipt sent successfully"},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
