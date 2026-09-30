"""
The indexing pipeline: LOAD -> CHUNK -> EMBED -> STORE.

`document_index` is the single entry point; each stage is its own function so
it can be run and tested in isolation.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.documents.models import Chunk, Document
from apps.rag.providers import embeddings_get
from apps.rag.services.chunking import text_chunk
from apps.rag.services.loaders import document_load

logger = logging.getLogger(__name__)


def _document_status_set(*, document: Document, status: str, error: str = "") -> Document:
    document.status = status
    document.error = error
    document.full_clean()
    document.save(update_fields=["status", "error", "updated_at"])

    return document


def document_index(*, document: Document) -> Document:
    """
    Runs the whole pipeline for one document and records the outcome on it.

    Failures are captured as status=FAILED + error (and logged) rather than
    raised: the upload API still returns the document, and `reindex` can retry.
    """
    _document_status_set(document=document, status=Document.Status.PROCESSING)

    try:
        # 1. LOAD: file bytes -> text units (pages for PDFs)
        loaded = document_load(document=document)

        # 2. CHUNK: text units -> overlapping passages
        chunks = text_chunk(
            docs=loaded,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            mime_type=document.mime_type,
        )

        # 3. EMBED: passages -> vectors (one call, batched by the provider)
        embeddings = embeddings_get()
        vectors = embeddings.embed_documents([chunk.page_content for chunk in chunks])

        # 4. STORE: replace any previous chunks atomically
        with transaction.atomic():
            Chunk.objects.filter(document=document).delete()

            Chunk.objects.bulk_create(
                [
                    Chunk(
                        document=document,
                        index=position,
                        text=chunk.page_content,
                        char_count=len(chunk.page_content),
                        metadata=chunk.metadata,
                        embedding=vector,
                    )
                    for position, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
                ]
            )

            document.chunk_count = len(chunks)
            document.embedding_model = f"{settings.EMBEDDING_PROVIDER}:{settings.EMBEDDING_MODEL}"
            document.indexed_at = timezone.now()
            _document_status_set(document=document, status=Document.Status.READY)

    except Exception as exc:
        logger.exception("Indexing failed for document %s", document.id)
        _document_status_set(document=document, status=Document.Status.FAILED, error=str(exc))

    return document
