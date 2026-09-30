from uuid import UUID

from django.db.models import QuerySet

from apps.users.models import BaseUser


def user_get(*, user_id: UUID) -> BaseUser | None:
    return BaseUser.objects.filter(id=user_id).first()


def user_list() -> QuerySet[BaseUser]:
    return BaseUser.objects.order_by("created_at")
