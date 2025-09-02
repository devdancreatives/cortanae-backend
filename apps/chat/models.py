from django.db import models
from django.contrib.auth import get_user_model

from cortanae.generic_utils.models_utils import BaseModelMixin


User = get_user_model()


class Room(BaseModelMixin):
    sender = models.ForeignKey(
        User, related_name="author", on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        User, related_name="reciepent", on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}-{self.sender}-{self.receiver}"

    

class Chat(BaseModelMixin):
    room_id = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="chats"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sender_msg"
    )
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="friend_msg"
    )
    text = models.TextField()
    slug = models.CharField(max_length=300, unique=True, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    has_seen = models.BooleanField(default=False)

    def __str__(self):
        return "%s - %s" % (self.id, self.date)
    
