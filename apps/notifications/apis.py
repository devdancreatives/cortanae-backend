from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.notifications.models import Notification, FCMDevice
from apps.notifications.serializers import (
    NotificationSerializer,
    FCMNotificationSerializer,
)
from rest_framework import status


class GetAllUserNotifications(ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(user=user)
        return queryset


class GetSingleNotification(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class MarkNotificationRead(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        notif = Notification.objects.filter(id=pk, user=request.user).first()
        if not notif:
            return Response({"detail": "Not found."}, status=404)
        notif.is_read = True
        notif.save(update_fields=["is_read", "read_at"])
        return Response(
            {"detail": "Marked as read."}, status=status.HTTP_200_OK
        )


class MarkAllNotificationsRead(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        return Response({"detail": "All marked as read."})


class FCMDeviceCreateView(CreateAPIView):
    queryset = FCMDevice.objects.all()
    serializer_class = FCMNotificationSerializer
    permission_classes = [IsAuthenticated]
   
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data.get("token")

        # Check if token already exists for this user
        device, created = FCMDevice.objects.get_or_create(
            user=request.user,
            token=token,
        )

        # If it already exists, just return it back
        response_serializer = self.get_serializer(device)
        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED
        )


class FCMDDeleteView(APIView):
    queryset = FCMDevice.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = FCMNotificationSerializer

    def post(self, request, *args, **kwargs):
        serializer = FCMNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        
        device = FCMDevice.objects.filter(token=token, user=request.user).first()
        if not device:
            return Response({"detail": "Not found."}, status=404)
        device.delete()
        return Response({"detail": "Deleted."}, status=status.HTTP_200_OK)

