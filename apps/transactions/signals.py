from django.core.checks import messages
from django.db import IntegrityError
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from typing import Dict

import string
import uuid
from random import choices
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ReturnList

from apps.notifications.models import NotificationType
from apps.notifications.service.notification_service import send_notification

from .models import Transaction, TransactionHistory, TxCategory, TxStatus


# # Store old values before save
@receiver(pre_save, sender=Transaction)
def store_old_transaction_state(sender, instance, **kwargs):
    if instance.pk:  # Only if updating, not creating
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_values = model_to_dict(old_instance)
        except sender.DoesNotExist:
            instance._old_values = {}
    else:
        instance._old_values = {}


@receiver(pre_save, sender=Transaction)
def create_transaction_reference(sender, instance, **kwargs):
    """Generate a unique uppercase reference if missing."""
    if instance.reference:
        return

    candidate = "".join(choices(string.ascii_uppercase + string.digits, k=8))
    ref = f"TRX{candidate}"

    if Transaction.objects.filter(reference=ref).exists():
        ref = f"TRX{uuid.uuid4().hex[:8].upper()}"

    instance.reference = ref
    print(f"[SIGNAL] Generated Transaction reference={instance.reference}")


@receiver(post_save, sender=Transaction)
def create_transaction_history(sender, instance, created, **kwargs):
    if created:
        TransactionHistory.objects.create(
            transaction=instance,
        )


def _is_success_status(status: str) -> bool:
    # Support legacy "successful" alongside enum COMPLETED
    return status in {TxStatus.SUCCESSFUL, "successful"}


@receiver(post_save, sender=Transaction)
def credit_account_on_successful_deposit(
    sender, instance: Transaction, created: bool, **kwargs
):
    """
    When a Transaction is a DEPOSIT and status is successful/completed,
    credit the destination account once. If a history row already exists,
    update it instead of creating a duplicate.
    """
    # --- Preconditions ---
    if instance.category != TxCategory.DEPOSIT:
        return
    if not _is_success_status(instance.status):
        return
    if not instance.destination_account_id:
        print("[SIG] Deposit has no destination_account; skipping credit.")
        return
    if not instance.account_type:
        print("[SIG] Deposit missing account_type; skipping credit.")
        return
    if not instance.amount or instance.amount <= 0:
        print("[SIG] Invalid amount; skipping credit.")
        return

    # Idempotency: only skip if we've already posted credit for THIS tx
    already_credited = instance.history.filter(
        metadata__credit_posted=True
    ).exists()
    if already_credited:
        print(
            f"[SIG] Credit already posted • ref={instance.reference} • skipping."
        )
        return

    amt: Decimal = instance.amount

    with transaction.atomic():
        # Lock account to avoid race conditions
        acct = (
            type(instance.destination_account)
            .objects.select_for_update()
            .get(pk=instance.destination_account_id)
        )

        if instance.account_type == "savings":
            type(acct).objects.filter(pk=acct.pk).update(
                savings_balance=F("savings_balance") + amt
            )
            new_balance = (
                type(acct)
                .objects.values_list("savings_balance", flat=True)
                .get(pk=acct.pk)
            )
            acc_label = "SAVINGS"
        elif instance.account_type == "checking":
            type(acct).objects.filter(pk=acct.pk).update(
                checking_balance=F("checking_balance") + amt
            )
            new_balance = (
                type(acct)
                .objects.values_list("checking_balance", flat=True)
                .get(pk=acct.pk)
            )
            acc_label = "CHECKING"
        else:
            print(
                f"[SIG] Unknown account_type='{instance.account_type}'; skipping credit."
            )
            return

        print(
            f"[SIG] Credited {acc_label} {amt} • new_balance={new_balance} • ref={instance.reference}"
        )

        # ---- Upsert a history entry instead of always creating a new one ----
        # Prefer updating an existing 'details_update' row if present
        hist = instance.history.order_by("created_at").first()

        meta_patch = {
            "credit_posted": True,
            "account_type": instance.account_type,
            "amount": str(amt),
        }
        note_patch = f"Auto‑credit posted to {instance.account_type} account."

        if hist:
            # Merge metadata and append note (no duplicate rows)
            metadata = dict(hist.metadata or {})
            metadata.update(meta_patch)
            hist.metadata = metadata
            hist.note = f"{(hist.note or '').strip()} • {note_patch}".strip(
                " •"
            )
            hist.save(update_fields=["metadata", "note", "updated_at"])
            content = f"{amt} has been credited into your {acc_label} account. New balance: {new_balance}"
            mail_options = (
                {
                    "to": instance.destination_account.user.email,
                    "subject": "Deposit Successful",
                    "body": content,
                }
                if instance.destination_account.user.email_notifications
                else None
            )

            # send_notification(
            #     user=instance.destination_account.user,
            #     content=content,
            #     title="Deposit Successful",
            #     type=NotificationType.TRANSACTION,
            #     mail_options=mail_options,
            # )

            print(
                f"[SIG] Updated existing history • id={hist.id} • ref={instance.reference}"
            )
        else:
            # Create a single clear row for this side-effect
            TransactionHistory.objects.create(
                transaction=instance,
                metadata=meta_patch,
                note=note_patch,
            )

            content = f"{amt} has been credited into your {acc_label} account. New balance: {new_balance}"
            mail_options = (
                {
                    "to": instance.destination_account.user.email,
                    "subject": "Deposit Successful",
                    "body": content,
                }
                if instance.destination_account.user.email_notifications
                else None
            )

            send_notification(
                user=instance.destination_account.user,
                content=content,
                title="Deposit Successful",
                type=NotificationType.TRANSACTION,
                mail_options=mail_options,
            )
            print(
                f"[SIG] Created history (credit marker) • ref={instance.reference}"
            )


MESSAGES: Dict[str, Dict[str, Dict[str, str]]] = {
    TxCategory.DEPOSIT: {
        TxStatus.PENDING: {
            "title": "Deposit Pending",
            "message": "Your deposit of {amount} is being processed.",
        },
        TxStatus.SUCCESSFUL: {
            "title": "Deposit Successful",
            "message": "Your deposit of {amount} has been completed successfully.",
        },
        TxStatus.FAILED: {
            "title": "Deposit Failed",
            "message": "Your deposit of {amount} could not be completed. Please try again.",
        },
    },
    TxCategory.WITHDRAWAL: {
        TxStatus.PENDING: {
            "title": "Withdrawal Pending",
            "message": "Your withdrawal of {amount} is awaiting confirmation.",
        },
        TxStatus.SUCCESSFUL: {
            "title": "Withdrawal Successful",
            "message": "Your withdrawal of {amount} was processed successfully.",
        },
        TxStatus.FAILED: {
            "title": "Withdrawal Failed",
            "message": "Your withdrawal of {amount} could not be completed.",
        },
    },
    TxCategory.TRANSFER_EXT: {
        TxStatus.PENDING: {
            "title": "Transfer Pending",
            "message": "Your transfer of {amount} is being processed.",
        },
        TxStatus.SUCCESSFUL: {
            "title": "Transfer Successful",
            "message": "Your transfer of {amount} has been completed.",
        },
        TxStatus.FAILED: {
            "title": "Transfer Failed",
            "message": "Your transfer of {amount} could not be completed.",
        },
    },
    TxCategory.TRANSFER_INT: {
        TxStatus.PENDING: {
            "title": "Payment Processing",
            "message": "Your payment of {amount} is being processed.",
        },
        TxStatus.SUCCESSFUL: {
            "title": "Payment Successful",
            "message": "Your payment of {amount} was successful.",
        },
        TxStatus.FAILED: {
            "title": "Payment Failed",
            "message": "Your payment of {amount} failed.",
        },
    },
}


# def build_transaction_message(transaction: Transaction) -> Dict[str, str]:
#     """
#     Returns a dictionary containing the title and message
#     based on transaction category and status.
#     """
#     category = transaction.category
#     status = transaction.status
#     amount = transaction.amount

#     # get message template
#     template = MESSAGES.get(category, {}).get(
#         status,
#         {
#             "title": "Unknown Transaction",
#             "message": "Your transaction of {amount} has an unknown status.",
#         },
#     )

#     return {
#         "title": template["title"],
#         "message": template["message"].format(amount=amount),
#     }


# @receiver(post_save, sender=Transaction)
# def transaction_signal(sender, instance, created, **kwargs):

#     if instance or created:
#         built_message = build_transaction_message(instance)
#         send_notification(
#             (
#                 instance.destination_account.user
#                 if TxCategory.DEPOSIT
#                 else instance.source_account.user
#             ),
#             built_message["title"],
#             built_message["message"],
#             type=NotificationType.TRANSACTION,
#         )
