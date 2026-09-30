from pathlib import PurePosixPath

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.documents.models import Document
from apps.users.models import BaseUser

GENERIC_MIME_TYPES = {"", None, "application/octet-stream", "binary/octet-stream"}


def document_mime_detect(*, file: UploadedFile) -> str:
    """
    Browsers/curl are unreliable about mime types (".md" often arrives as
    text/plain or octet-stream), so a known extension wins over the header.
    """
    extension = PurePosixPath(file.name or "").suffix.lower()

    if extension in settings.DOCUMENT_EXTENSION_MIME_TYPES:
        return settings.DOCUMENT_EXTENSION_MIME_TYPES[extension]

    content_type = getattr(file, "content_type", None)

    if content_type in GENERIC_MIME_TYPES:
        return "application/octet-stream"

    return content_type


def document_create(
    *,
    owner: BaseUser,
    file: UploadedFile,
    title: str | None = None,
    index: bool = True,
) -> Document:
    """
    Store the upload, then (synchronously, for now) push it through the RAG
    indexing pipeline. A failed index is recorded on the document rather than
    raised, so the caller always gets the document back with status/error.
    """
    document = Document(
        owner=owner,
        file=file,
        title=title or file.name,
        mime_type=document_mime_detect(file=file),
        size=file.size,
    )

    document.full_clean()
    document.save()

    if index:
        # Imported here to keep documents -> rag a runtime dependency only.
        from apps.rag.services import document_index

        document = document_index(document=document)

    return document


def document_reindex(*, document: Document) -> Document:
    from apps.rag.services import document_index

    return document_index(document=document)


def document_delete(*, document: Document) -> None:
    document.file.delete(save=False)
    document.delete()
