import uuid

from django.db import models
from django.conf import settings


class UUIDPrimaryKeyModelMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampModelMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class NoUserActionBaseModelMixin(UUIDPrimaryKeyModelMixin, TimestampModelMixin):
    class Meta:
        abstract = True
        
class BaseModelMixin(UUIDPrimaryKeyModelMixin, TimestampModelMixin):

    class Meta:
        abstract = True


class ActiveInactiveModelMixin(models.Model):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class SoftDeleteModelManagerMixin(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        return super().get_queryset()

    def deleted(self):
        return super().get_queryset().filter(is_deleted=True)


class SoftDeleteModelMixin(models.Model):
    is_deleted = models.BooleanField(default=False)

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

    def restore(self):
        self.is_deleted = False
        self.save()

    def is_soft_deleted(self):
        return self.is_deleted

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    objects = models.Manager()
    cobjects = SoftDeleteModelManagerMixin()

    class Meta:
        abstract = True


class BaseSoftDeleteModelMixin(
    BaseModelMixin,
    SoftDeleteModelMixin,
):
    class Meta:
        abstract = True



class BaseActiveInactiveModelMixin(
    BaseModelMixin,
    ActiveInactiveModelMixin,
):
    class Meta:
        abstract = True


django_media_private_storage = None


def get_django_media_private_storage():
    if not settings.FILE_STORAGE_SETTINGS:
        return None
    return None
