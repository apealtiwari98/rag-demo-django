from unittest import mock

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from langchain_core.embeddings import DeterministicFakeEmbedding
from rest_framework.test import APIClient, APITestCase

from apps.documents.models import Document
from apps.documents.tests.factories import MARKDOWN_FIXTURE, ChunkFactory, DocumentFactory
from apps.users.tests.factories import UserFactory

fake_embeddings = DeterministicFakeEmbedding(size=settings.EMBEDDING_DIM)


class DocumentApisTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @mock.patch("apps.rag.services.indexing.embeddings_get", return_value=fake_embeddings)
    def test_upload_returns_indexed_document(self, _):
        file = SimpleUploadedFile("notes.md", MARKDOWN_FIXTURE, content_type="text/markdown")

        response = self.client.post(reverse("api_v1:documents:create"), {"file": file}, format="multipart")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], Document.Status.READY)
        self.assertGreaterEqual(response.data["chunk_count"], 1)

    def test_upload_rejects_unsupported_type_with_error_shape(self):
        file = SimpleUploadedFile("app.exe", b"MZ", content_type="application/x-msdownload")

        response = self.client.post(reverse("api_v1:documents:create"), {"file": file}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Validation error")
        self.assertIn("mime_type", response.data["extra"]["fields"])

    def test_list_is_paginated_and_scoped(self):
        DocumentFactory.create_batch(2, owner=self.user)
        DocumentFactory()

        response = self.client.get(reverse("api_v1:documents:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_detail_of_other_users_document_is_404(self):
        theirs = DocumentFactory()

        response = self.client.get(reverse("api_v1:documents:detail", kwargs={"document_id": theirs.id}))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {"message": "Not found.", "extra": {}})

    def test_chunks_endpoint_lists_chunk_text(self):
        document = DocumentFactory(owner=self.user)
        ChunkFactory(document=document, index=0, text="first")

        response = self.client.get(reverse("api_v1:documents:chunks", kwargs={"document_id": document.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["text"], "first")
        self.assertNotIn("embedding", response.data["results"][0])

    def test_delete(self):
        document = DocumentFactory(owner=self.user)

        response = self.client.delete(reverse("api_v1:documents:delete", kwargs={"document_id": document.id}))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Document.objects.filter(id=document.id).exists())

    def test_unauthenticated_is_401(self):
        response = APIClient().get(reverse("api_v1:documents:list"))

        self.assertEqual(response.status_code, 401)
