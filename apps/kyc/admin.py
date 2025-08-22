from django.contrib import admin
from django.utils.html import format_html
from .models import KYC


# ---------- Reusable base admin ----------
class BaseStampedAdmin(admin.ModelAdmin):
    """Common admin options for models inheriting BaseModelMixin (created_at/updated_at)."""
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        print(f"[ADMIN] Saving {obj.__class__.__name__} pk={getattr(obj, 'pk', None)} by {request.user}")
        super().save_model(request, obj, form, change)

# ---------- KYC admin ----------
@admin.register(KYC)
class KYCAdmin(BaseStampedAdmin):
    list_display = (
        "id",
        "user",
        "full_name",
        "email",
        "phone_number",
        "status",
        "country",
        "account_type",
        "created_at",
    )
    list_filter = (
        "status",
        "account_type",
        "gender",
        "country",
        "date_of_birth",
        "created_at",
    )
    search_fields = (
        "full_name",
        "email",
        "phone_number",
        "ssn",
        "user__username",
        "user__email",
        "city",
        "state",
        "nationality",
    )
    fieldsets = (
        ("User Link", {"fields": ("user",)}),
        ("Identity", {
            "fields": (
                "full_name", "email", "phone_number", "title", "gender", "date_of_birth", "ssn",
            )
        }),
        ("Residence", {"fields": ("address", "city", "state", "zip_code", "country", "nationality")}),
        ("Financial Profile", {"fields": ("account_type", "income_range")}),
        ("Next of Kin", {"fields": ("kin_name", "relationship", "kin_address", "kin_date_of_birth")}),
        ("Documents", {"fields": ("document_type", "document_front", "document_back", "passport_image",
                                  "document_front_preview", "document_back_preview", "passport_image_preview")}),
        ("Status", {"fields": ("status", "error_message")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = BaseStampedAdmin.readonly_fields + (
        "document_front_preview",
        "document_back_preview",
        "passport_image_preview",
    )
    actions = ("mark_approved", "mark_rejected", "mark_pending")

    # ---- Small previews for Cloudinary images (clickable) ----
    @admin.display(description="Document Front")
    def document_front_preview(self, obj):
        return self._image_link(obj.document_front)

    @admin.display(description="Document Back")
    def document_back_preview(self, obj):
        return self._image_link(obj.document_back)

    @admin.display(description="Passport Image")
    def passport_image_preview(self, obj):
        return self._image_link(obj.passport_image)

    def _image_link(self, cloudinary_field):
        try:
            if cloudinary_field and getattr(cloudinary_field, "url", None):
                return format_html('<a href="{}" target="_blank">Open</a>', cloudinary_field.url)
        except Exception as exc:
            print(f"[ADMIN][KYC] Preview error: {exc}")
        return "-"

    # ---- Quick status actions with debug prints ----
    def _bulk_status_update(self, request, queryset, status_value):
        count = queryset.update(status=status_value)
        print(f"[ADMIN][KYC] Set status='{status_value}' for {count} record(s) by {request.user}")

    def mark_approved(self, request, queryset):
        self._bulk_status_update(request, queryset, "approved")
    mark_approved.short_description = "Mark selected as Approved"

    def mark_rejected(self, request, queryset):
        self._bulk_status_update(request, queryset, "rejected")
    mark_rejected.short_description = "Mark selected as Rejected"

    def mark_pending(self, request, queryset):
        self._bulk_status_update(request, queryset, "pending")
    mark_pending.short_description = "Mark selected as Pending"