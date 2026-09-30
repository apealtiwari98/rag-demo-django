import uuid

from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    HackSoft-style base model, plus a UUID primary key so ids are safe to
    expose in URLs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(db_index=True, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
