from rest_framework import serializers

from apps.notifications.models import FCMDevice, Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class FCMNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = ["token"]
