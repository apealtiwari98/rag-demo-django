from django.contrib import admin

from apps.rag.models import QueryLog


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ("question", "user", "llm_model", "top_k", "latency_ms", "created_at")
    list_filter = ("llm_model", "embedding_model")
    search_fields = ("question", "answer")
    readonly_fields = [f.name for f in QueryLog._meta.fields]
