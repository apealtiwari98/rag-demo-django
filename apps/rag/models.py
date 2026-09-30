from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class QueryLog(BaseModel):
    """
    One question through the RAG pipeline: what was asked, what was retrieved
    (with similarity scores), what the LLM answered. This is the raw material
    for evaluating retrieval quality later.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="queries")

    question = models.TextField()
    answer = models.TextField()
    # [{"chunk_id", "document_id", "document_title", "index", "score", "page"}, ...]
    sources = models.JSONField(default=list, blank=True)

    llm_model = models.CharField(max_length=255)
    embedding_model = models.CharField(max_length=255)
    top_k = models.PositiveIntegerField()
    latency_ms = models.PositiveIntegerField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.question[:80]
