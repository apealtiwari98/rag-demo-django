from unittest import mock

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from langchain_core.embeddings import DeterministicFakeEmbedding

from apps.documents.models import Chunk, Document
from apps.documents.services import document_create, document_delete, document_mime_detect
from apps.documents.tests.factories import MARKDOWN_FIXTURE, ChunkFactory, DocumentFactory
from apps.users.tests.factories import UserFactory

fake_embeddings = DeterministicFakeEmbedding(size=settings.EMBEDDING_DIM)


class DocumentMimeDetectTests(TestCase):
    def test_known_extension_wins_over_generic_header(self):
        file = SimpleUploadedFile("notes.md", b"# hi", content_type="application/octet-stream")

        self.assertEqual(document_mime_detect(file=file), "text/markdown")

    def test_unknown_extension_falls_back_to_header(self):
        file = SimpleUploadedFile("data.bin", b"x", content_type="application/pdf")

        self.assertEqual(document_mime_detect(file=file), "application/pdf")

    def test_unknown_extension_and_generic_header(self):
        file = SimpleUploadedFile("data.bin", b"x", content_type="application/octet-stream")

        self.assertEqual(document_mime_detect(file=file), "application/octet-stream")


@mock.patch("apps.rag.services.indexing.embeddings_get", return_value=fake_embeddings)
class DocumentCreateTests(TestCase):
    def setUp(self):
        self.owner = UserFactory()

    def test_create_stores_file_and_indexes_it(self, _):
        file = SimpleUploadedFile("notes.md", MARKDOWN_FIXTURE, content_type="application/octet-stream")

        document = document_create(owner=self.owner, file=file)

        self.assertEqual(document.title, "notes.md")
        self.assertEqual(document.mime_type, "text/markdown")
        self.assertEqual(document.size, len(MARKDOWN_FIXTURE))
        self.assertEqual(document.status, Document.Status.READY)
        self.assertGreaterEqual(document.chunk_count, 1)
        self.assertEqual(Chunk.objects.filter(document=document).count(), document.chunk_count)
        self.assertTrue(document.file.name.startswith(f"documents/{self.owner.id}/{document.id}/"))

    def test_create_with_index_false_leaves_document_pending(self, _):
        file = SimpleUploadedFile("notes.txt", b"plain text", content_type="text/plain")

        document = document_create(owner=self.owner, file=file, index=False)

        self.assertEqual(document.status, Document.Status.PENDING)
        self.assertEqual(document.chunk_count, 0)

    def test_create_rejects_unsupported_file_type(self, _):
        file = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/x-msdownload")

        with self.assertRaises(ValidationError):
            document_create(owner=self.owner, file=file)

        self.assertEqual(Document.objects.count(), 0)


class DocumentDeleteTests(TestCase):
    def test_delete_removes_document_chunks_and_file(self):
        document = DocumentFactory()
        ChunkFactory.create_batch(2, document=document)
        storage, path = document.file.storage, document.file.name

        document_delete(document=document)

        self.assertFalse(Document.objects.filter(id=document.id).exists())
        self.assertEqual(Chunk.objects.count(), 0)
        self.assertFalse(storage.exists(path))
