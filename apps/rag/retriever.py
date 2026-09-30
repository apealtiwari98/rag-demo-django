"""
A LangChain `BaseRetriever` over our selector, so the Django-backed vector
store composes with LCEL chains exactly like any off-the-shelf vector store.
"""

from typing import Any
from uuid import UUID

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document as LCDocument
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from apps.rag.selectors import ChunkHit, chunk_search


def chunk_hit_to_lc_document(hit: ChunkHit) -> LCDocument:
    chunk = hit.chunk

    return LCDocument(
        page_content=chunk.text,
        metadata={
            **chunk.metadata,
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "document_title": chunk.document.title,
            "index": chunk.index,
            "score": hit.score,
        },
    )


class DjangoChunkRetriever(BaseRetriever):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user: Any
    top_k: int
    document_ids: list[UUID] | None = None

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[LCDocument]:
        hits = chunk_search(user=self.user, question=query, top_k=self.top_k, document_ids=self.document_ids)

        return [chunk_hit_to_lc_document(hit) for hit in hits]
