from uuid import uuid4
from decimal import Decimal

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import AdminSplitDateTime
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Transaction, TransactionMeta, TransactionHistory, TxStatus


# ---------------- Inlines ----------------
class TransactionMetaInline(admin.StackedInline):
    model = TransactionMeta
    extra = 0
    max_num = 1
    can_delete = True
    readonly_fields = ("payment_proof_link", "payment_proof_2_link")

    fieldsets = (
        ("External Beneficiary (Wire/Bank)", {
            "fields": ("beneficiary_name", "beneficiary_account_number", "beneficiary_bank_name",
                       "banking_routing_number", "bank_swift_code", "recipient_address", "description",)
        }),
        ("Attachments", {
            "fields": ("payment_proof", "payment_proof_link", "payment_proof_2", "payment_proof_2_link")
        }),
    )

    @admin.display(description="Payment Proof (Cloudinary)")
    def payment_proof_link(self, obj: TransactionMeta):
        try:
            if obj and obj.payment_proof:
                return format_html('<a href="{}" target="_blank">Open</a>', obj.payment_proof.build_url())
        except Exception:
            pass
        return "-"

    @admin.display(description="Receipt (Cloudinary)")
    def payment_proof_2_link(self, obj: TransactionMeta):
        try:
            if obj and obj.payment_proof_2:
                return format_html('<a href="{}" target="_blank">Open</a>', obj.payment_proof_2.build_url())
        except Exception:
            pass
        return "-"


# ---------------- Admin ----------------
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Django 4.2 admin with:
    - Meta inline
    - Status quick actions
    - Reference autogeneration
    - Debug prints
    """
    inlines = [TransactionMetaInline]

    list_display = (
        "reference", "category", "method",
        "amount_with_currency", "fee_amount", "net_amount_display",
        "status_badge", "source_link", "destination_link", "created_at",
    )
    list_filter = ("category", "method", "status", "currency", "created_at")
    search_fields = (
        "reference", "error_message", "currency",
        "meta__beneficiary_name", "meta__beneficiary_account_number", "meta__beneficiary_bank_name",
    )
    # Keep real timestamps readonly; we write created_at via explicit UPDATE after save.
    readonly_fields = ("created_at", "updated_at", "net_amount_display")
    ordering = ("-created_at",)

    fieldsets = (
        ("Identifiers", {"fields": ("status", "reference")}),
        ("Classification", {"fields": ("category", "method", "account_type")}),
        ("Participants", {"fields": ("source_account", "destination_account")}),
        ("Amounts", {"fields": ("amount", "fee_amount", "currency", "net_amount_display")}),
        ("Context", {"fields": ("error_message", "initiated_by",
                                "created_at", "updated_at",)}),
    )

    actions = ("mark_successful", "mark_cancelled", "mark_failed")

    # -------- Display helpers --------
    @admin.display(description="Amount")
    def amount_with_currency(self, obj: Transaction) -> str:
        return f"{obj.amount} {obj.currency}"

    @admin.display(description="Net Amount")
    def net_amount_display(self, obj: Transaction) -> str:
        net = (obj.amount or Decimal("0.00")) - (obj.fee_amount or Decimal("0.00"))
        return f"{net} {obj.currency}"

    @admin.display(description="Status")
    def status_badge(self, obj: Transaction):
        color = {
            TxStatus.PENDING: "#b58900",
            TxStatus.SUCCESSFUL: "#2aa198",
            TxStatus.CANCELLED: "#586e75",
            TxStatus.FAILED: "#dc322f",
        }.get(obj.status, "#657b83")
        return format_html(
            '<span style="padding:2px 8px;border-radius:12px;background:{};color:white;font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )

    @admin.display(description="Source")
    def source_link(self, obj: Transaction):
        if not obj.source_account_id:
            return "-"
        url = reverse("admin:accounts_account_change", args=[obj.source_account_id])
        return format_html('<a href="{}">#{}</a>', url, obj.source_account_id)

    @admin.display(description="Destination")
    def destination_link(self, obj: Transaction):
        if not obj.destination_account_id:
            return "-"
        url = reverse("admin:accounts_account_change", args=[obj.destination_account_id])
        return format_html('<a href="{}">#{}</a>', url, obj.destination_account_id)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("source_account", "destination_account", "initiated_by").prefetch_related("history")

    # -------- Save / Audit --------
    def save_model(self, request, obj: Transaction, form, change):
        # Ensure reference exists
        if not obj.reference:
            obj.reference = uuid4().hex[:12].upper()

        # Track previous status
        previous_status = None
        if change:
            try:
                previous_status = Transaction.objects.only("status").get(pk=obj.pk).status
            except Transaction.DoesNotExist:
                previous_status = None

        print(f"[ADMIN] Saving Transaction • ref={obj.reference} • status={obj.status} • by={request.user}")
        super().save_model(request, obj, form, change)

        # Log status change (optional)
        if previous_status and previous_status != obj.status:
            TransactionHistory.objects.create(
                transaction=obj,
                metadata={"from": previous_status, "to": obj.status},
                note=f"Status changed by {request.user}",
            )
            print(f"[ADMIN] History logged • ref={obj.reference} • {previous_status} -> {obj.status}")

    # -------- Bulk Actions --------
    def _bulk_set_status(self, request, queryset, new_status: str, label: str):
        count = 0
        for tx in queryset:
            old = tx.status
            if old == new_status:
                continue
            tx.status = new_status
            tx.save(update_fields=["status", "updated_at"])
            TransactionHistory.objects.create(
                transaction=tx,
                metadata={"from": old, "to": new_status, "action": "bulk_admin"},
                note=f"{label} by {request.user}",
            )
            count += 1
            print(f"[ADMIN] Bulk {label} • ref={tx.reference} • {old} -> {new_status}")
        self.message_user(request, f"{count} transaction(s) marked as {label.lower()}.", level=messages.SUCCESS)

    @admin.action(description="Mark as Successful")
    def mark_successful(self, request, queryset):
        self._bulk_set_status(request, queryset, TxStatus.SUCCESSFUL, "Successful")

    @admin.action(description="Mark as Cancelled")
    def mark_cancelled(self, request, queryset):
        self._bulk_set_status(request, queryset, TxStatus.CANCELLED, "Cancelled")

    @admin.action(description="Mark as Failed")
    def mark_failed(self, request, queryset):
        self._bulk_set_status(request, queryset, TxStatus.FAILED, "Failed")
