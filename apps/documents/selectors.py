from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from django.http import Http404

from apps.documents.filters import DocumentFilter
from apps.documents.models import Chunk, Document
from apps.users.models import BaseUser


def document_list(*, owner: BaseUser, filters: dict[str, Any] | None = None) -> QuerySet[Document]:
    filters = filters or {}

    qs = Document.objects.filter(owner=owner)

    return DocumentFilter(filters, qs).qs


def document_get(*, owner: BaseUser, document_id: UUID) -> Document:
    """
    Ownership is enforced here, not in the view: a document that belongs to
    someone else is indistinguishable from one that doesn't exist.
    """
    document = Document.objects.filter(owner=owner, id=document_id).first()

    if document is None:
        raise Http404("Document not found.")

    return document


def chunk_list_for_document(*, owner: BaseUser, document_id: UUID) -> QuerySet[Chunk]:
    document = document_get(owner=owner, document_id=document_id)

    return Chunk.objects.filter(document=document).order_by("index")
