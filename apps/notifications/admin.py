from django.contrib import admin
from .models import Notification, FCMDevice

# Register your models here.
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "type", "is_read", "created_at")
    list_filter = ("is_read", "type", "created_at", "user")
    search_fields = ("title", "content", "user__username", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "read_at")

admin.site.register(FCMDevice)
