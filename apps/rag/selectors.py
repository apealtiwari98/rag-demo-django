"""
RETRIEVE: the read side of RAG.

Embed the question with the *same* model used at index time, then ask
Postgres for the nearest chunk vectors. Ownership filtering happens in the
same SQL query, so a user can never retrieve someone else's chunks.
"""

from dataclasses import dataclass
from uuid import UUID

from pgvector.django import CosineDistance

from apps.documents.models import Chunk, Document
from apps.rag.providers import embeddings_get
from apps.users.models import BaseUser


@dataclass(frozen=True)
class ChunkHit:
    chunk: Chunk
    # Cosine similarity in [-1, 1]; 1.0 means identical direction.
    score: float


def chunk_search(
    *,
    user: BaseUser,
    question: str,
    top_k: int,
    document_ids: list[UUID] | None = None,
) -> list[ChunkHit]:
    query_vector = embeddings_get().embed_query(question)

    qs = Chunk.objects.filter(document__owner=user, document__status=Document.Status.READY)

    if document_ids:
        qs = qs.filter(document_id__in=document_ids)

    # pgvector's `<=>` operator; the HNSW index on Chunk.embedding serves it.
    qs = (
        qs.select_related("document")
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:top_k]
    )

    return [ChunkHit(chunk=chunk, score=1.0 - chunk.distance) for chunk in qs]
