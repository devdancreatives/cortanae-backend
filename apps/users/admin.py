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
                "verification_token",
            )
        }),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Profile", {"fields": ("phone_number", "country")}),
    )

    @admin.display(description="Full name")
    def get_full_name(self, obj):
        try:
            return obj.get_full_name()
        except Exception as exc:
            print(f"[ADMIN][User] get_full_name error: {exc}")
            return "-"

    # ----- Quick actions -----
    def mark_verified(self, request, queryset):
        updated = queryset.update(is_verified=True)
        print(f"[ADMIN][User] Marked verified: {updated} record(s) by {request.user}")
    mark_verified.short_description = "Mark selected users as Verified"

    def mark_unverified(self, request, queryset):
        updated = queryset.update(is_verified=False)
        print(f"[ADMIN][User] Un-verified: {updated} record(s) by {request.user}")
    mark_unverified.short_description = "Mark selected users as Unverified"

    def soft_delete(self, request, queryset):
        updated = queryset.update(is_deleted=True, is_active=False)
        print(f"[ADMIN][User] Soft-deleted (and deactivated): {updated} by {request.user}")
    soft_delete.short_description = "Soft delete (set is_deleted=True, deactivate)"

    def restore_user(self, request, queryset):
        updated = queryset.update(is_deleted=False, is_active=True)
        print(f"[ADMIN][User] Restored (and activated): {updated} by {request.user}")
    restore_user.short_description = "Restore user (set is_deleted=False, activate)"


# ---------- TokenValidator admin ----------
@admin.register(TokenValidator)
class TokenValidatorAdmin(BaseStampedAdmin):
    """Detail admin for TokenValidator records."""
    list_display = ("id", "user", "token_type", "token", "created_at")
    list_filter = ("token_type", "created_at")
    search_fields = ("user", "token")
    fieldsets = (
        ("Token", {"fields": ("user", "token_type", "token")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
