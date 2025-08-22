from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """Admin detail view for Account model"""

    list_display = (
        "id",
        "account_number",
        "account_name",
        "user",
        "balance",
        "account_type",
        "bank_name",
        "is_active",
        "created_at",
    )
    list_filter = ("account_type", "bank_name", "is_active", "created_at")
    search_fields = ("account_number", "account_name", "user__username", "bank_name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    fieldsets = (
        ("Account Info", {
            "fields": (
                "account_number",
                "account_name",
                "account_type",
                "bank_name",
                "balance",
            )
        }),
        ("User", {
            "fields": ("user",),
        }),
        ("Security", {
            "fields": ("account_pin",),
        }),
        ("Status", {
            "fields": ("is_active", "created_at", "updated_at"),
        }),
    )