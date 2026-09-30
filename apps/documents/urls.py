from django.urls import include, path

from apps.documents.apis import (
    DocumentChunkListApi,
    DocumentCreateApi,
    DocumentDeleteApi,
    DocumentDetailApi,
    DocumentListApi,
    DocumentReindexApi,
)

document_patterns = [
    path("", DocumentListApi.as_view(), name="list"),
    path("upload/", DocumentCreateApi.as_view(), name="create"),
    path("<uuid:document_id>/", DocumentDetailApi.as_view(), name="detail"),
    path("<uuid:document_id>/delete/", DocumentDeleteApi.as_view(), name="delete"),
    path("<uuid:document_id>/reindex/", DocumentReindexApi.as_view(), name="reindex"),
    path("<uuid:document_id>/chunks/", DocumentChunkListApi.as_view(), name="chunks"),
]

urlpatterns = [
    path("", include((document_patterns, "documents"))),
]
