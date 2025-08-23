from django.contrib import admin
from .models import Account


class BaseStampedAdmin(admin.ModelAdmin):
    """Common admin for models inheriting BaseModelMixin (created_at/updated_at)."""
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        print(f"[ADMIN] Saving {obj.__class__.__name__} pk={getattr(obj, 'pk', None)} by {request.user}")
        super().save_model(request, obj, form, change)


@admin.register(Account)
class AccountAdmin(BaseStampedAdmin):
    """Simple, clear detail admin for Account."""
    list_display = (
        "id",
        "account_name",
        "user",
        "checking_acc_number",
        "savings_acc_number",
        "checking_balance",
        "savings_balance",
        "total_balance",
        "bank_name",
        "is_active",
        "created_at",
    )
    list_filter = ("bank_name", "is_active", "created_at")
    search_fields = (
        "account_name",
        "checking_acc_number",
        "savings_acc_number",
        "user__email",
        "user__username",
        "bank_name",
    )

    fieldsets = (
        ("Owner", {"fields": ("user",)}),
        ("Account Numbers", {"fields": ("checking_acc_number", "savings_acc_number")}),
        ("Balances", {"fields": ("checking_balance", "savings_balance", "total_balance")}),
        ("Bank & Security", {"fields": ("bank_name",)}),
        ("Status & Timestamps", {"fields": ("is_active", "created_at", "updated_at")}),
    )

    # expose computed total as readonly in form
    readonly_fields = BaseStampedAdmin.readonly_fields + ("total_balance",)

    actions = ("reset_checking_balance", "reset_savings_balance")

    @admin.display(description="Total Balance")
    def total_balance(self, obj):
        try:
            return (obj.checking_balance or 0) + (obj.savings_balance or 0)
        except Exception as exc:
            print(f"[ADMIN][Account] total_balance error: {exc}")
            return 0

    # quick utilities with debug prints
    def reset_checking_balance(self, request, queryset):
        updated = queryset.update(checking_balance=0)
        print(f"[ADMIN][Account] Reset checking_balance to 0 for {updated} record(s) by {request.user}")
    reset_checking_balance.short_description = "Reset checking balance to 0"

    def reset_savings_balance(self, request, queryset):
        updated = queryset.update(savings_balance=0)
        print(f"[ADMIN][Account] Reset savings_balance to 0 for {updated} record(s) by {request.user}")
    reset_savings_balance.short_description = "Reset savings balance to 0"