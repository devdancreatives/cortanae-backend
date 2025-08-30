from django.db import models
from cortanae.generic_utils.account_verification import User
from cortanae.generic_utils.models_utils import BaseModelMixin
from cloudinary.models import CloudinaryField


class Message(BaseModelMixin):
    content = models.TextField()
    is_read = models.BooleanField(default=False)

    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_messages"
    )
    media_file = CloudinaryField(
        "attachment", resource_type="auto", null=True, blank=True
    )

    def __str__(self):
        return f"{self.sender} → {self.receiver}: {self.content[:30]}"

    class Meta:
        ordering = ["-created_at"]  # newest messages first
        indexes = [
            models.Index(fields=["sender", "receiver"]),
            models.Index(fields=["is_read"]),
        ]
