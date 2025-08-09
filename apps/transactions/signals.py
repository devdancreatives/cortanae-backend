from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from .models import Transaction, TransactionHistory


# Store old values before save
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


# Create history after save
@receiver(post_save, sender=Transaction)
def create_transaction_history(sender, instance, created, **kwargs):
    changed_by = getattr(instance, "_changed_by", None)

    if created:
        TransactionHistory.objects.create(
            transaction=instance,
            action="created",
            new_status=instance.status,
            changed_by=changed_by,
            metadata=model_to_dict(instance),
        )
    else:
        old_values = getattr(instance, "_old_values", {})
        new_values = model_to_dict(instance)

        changes = {}
        for field, old_value in old_values.items():
            new_value = new_values.get(field)
            if old_value != new_value:
                changes[field] = {"old": old_value, "new": new_value}

        if changes:
            action = (
                "status_change" if "status" in changes else "details_update"
            )
            TransactionHistory.objects.create(
                transaction=instance,
                action=action,
                previous_status=old_values.get("status"),
                new_status=new_values.get("status"),
                changed_by=changed_by,
                metadata=changes,
            )
