from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.common.models import BaseModel


def document_upload_to(instance: "Document", filename: str) -> str:
    return f"documents/{instance.owner_id}/{instance.id}/{filename}"


class Document(BaseModel):
    """
    An uploaded file. Its text is split into `Chunk`s by the RAG indexing
    pipeline; `status`/`error` expose what happened.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")

    file = models.FileField(upload_to=document_upload_to)
    title = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField(help_text="Bytes")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)

    chunk_count = models.PositiveIntegerField(default=0)
    # Recorded at index time so a later model switch is detectable.
    embedding_model = models.CharField(max_length=255, blank=True)
    indexed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        if self.mime_type not in settings.DOCUMENT_ALLOWED_MIME_TYPES:
            allowed = ", ".join(sorted(settings.DOCUMENT_ALLOWED_MIME_TYPES))
            raise ValidationError({"mime_type": f"Unsupported file type '{self.mime_type}'. Allowed: {allowed}."})

        if self.size > settings.DOCUMENT_MAX_SIZE_BYTES:
            limit_mb = settings.DOCUMENT_MAX_SIZE_BYTES // (1024 * 1024)
            raise ValidationError({"size": f"File is larger than the {limit_mb} MB limit."})

    @property
    def is_ready(self) -> bool:
        return self.status == self.Status.READY


class Chunk(BaseModel):
    """
    One piece of a document's text plus its embedding vector. This table IS
    the vector store: retrieval is a cosine-distance query against `embedding`.
    """

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")

    index = models.PositiveIntegerField(help_text="Position of the chunk within the document")
    text = models.TextField()
    char_count = models.PositiveIntegerField(default=0)
    # Anything the loader/splitter knows: page number, markdown headers, ...
    metadata = models.JSONField(default=dict, blank=True)

    embedding = VectorField(dimensions=settings.EMBEDDING_DIM)

    class Meta:
        ordering = ["document", "index"]
        constraints = [
            models.UniqueConstraint(fields=["document", "index"], name="chunk_unique_index_per_document"),
        ]
        indexes = [
            # Approximate nearest neighbour index for cosine distance (`<=>`).
            HnswIndex(
                name="chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document_id}#{self.index}"
