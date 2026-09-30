from django.contrib import admin

from apps.documents.models import Chunk, Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "mime_type", "status", "chunk_count", "embedding_model", "created_at")
    list_filter = ("status", "mime_type")
    search_fields = ("title", "owner__email")
    readonly_fields = ("id", "size", "status", "error", "chunk_count", "embedding_model", "indexed_at", "created_at", "updated_at")


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "index", "char_count", "created_at")
    list_filter = ("document",)
    search_fields = ("text",)
    # The raw vector is hundreds of floats; show a preview instead.
    exclude = ("embedding",)
    readonly_fields = ("id", "document", "index", "text", "char_count", "metadata", "embedding_preview", "created_at")

    @admin.display(description="Embedding")
    def embedding_preview(self, obj: Chunk) -> str:
        values = list(obj.embedding[:8])
        return f"dim={len(obj.embedding)} [{', '.join(f'{v:.4f}' for v in values)}, ...]"
