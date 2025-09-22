from django.db import models

from django.contrib.auth import get_user_model
from cortanae.generic_utils.models_utils import BaseModelMixin


User = get_user_model()


class NotificationType(models.TextChoices):
    TRANSACTION = "transaction", "Transaction"
    SECURITY = "security", "Security"
    SYSTEM = "system", "System"
    PROMOTION = "promotion", "Promotion"


# Create your models here.
class Notification(BaseModelMixin):
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    title = models.CharField(max_length=255, null=False, blank=False)
    content = models.TextField()
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="my_notifications"
    )
    type = models.CharField(
        choices=NotificationType.choices,
        default=NotificationType.choices,
        max_length=30,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["type"]),
        ]

    def __str__(self):
        return f"[{self.type}] {self.title} → {self.user.username}"


class FCMDevice(models.Model):
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User, related_name="fcm_devices", on_delete=models.CASCADE
    )
