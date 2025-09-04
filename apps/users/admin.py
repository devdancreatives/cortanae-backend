from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, TokenValidator


# ---------- Reusable base admin ----------
class BaseStampedAdmin(admin.ModelAdmin):
    """Common admin options for models inheriting BaseModelMixin."""
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        print(f"[ADMIN] Saving {obj.__class__.__name__} pk={getattr(obj, 'pk', None)} by {request.user}")
        super().save_model(request, obj, form, change)


# ---------- Custom User admin ----------
# ---------- Custom User admin ----------
@admin.register(User)
class UserAdmin(DjangoUserAdmin, BaseStampedAdmin):
    """Detail admin for custom User model."""

    list_display = (
        "id",
        "email",
        "username",
        "get_full_name",
        "phone_number",
        "country",
        "is_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "is_deleted",
        "last_login",
        "created_at",
    )

    list_filter = (
        "is_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "is_deleted",
        "country",
        "created_at",
    )

    search_fields = ("email", "username", "first_name", "last_name", "phone_number")
    readonly_fields = BaseStampedAdmin.readonly_fields + ("last_login", "date_joined")
    actions = ("mark_verified", "mark_unverified", "soft_delete", "restore_user")

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Profile", {
            "fields": (
                "phone_number",
                "country",
                "is_verified",
                "is_deleted",
                "email_notifications",
            )
        }),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    # ✅ FIX → Add email to add_fieldsets
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2"),
        }),
        ("Profile", {
            "fields": ("phone_number", "country"),
        }),
    )

# ---------- TokenValidator admin ----------
@admin.register(TokenValidator)
class TokenValidatorAdmin(BaseStampedAdmin):
    """Detail admin for TokenValidator records."""
    list_display = ("id", "user", "token_type", "is_active", "created_at")
    list_filter = ("token_type", "created_at")
    search_fields = ("user", "token")
    fieldsets = (
        ("Token", {"fields": ("user", "token_type", "token", "is_active", )}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
