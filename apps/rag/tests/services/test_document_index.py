from unittest import mock

from django.conf import settings
from django.test import TestCase
from langchain_core.embeddings import DeterministicFakeEmbedding

from apps.documents.models import Chunk, Document
from apps.documents.tests.factories import ChunkFactory, DocumentFactory
from apps.rag.services import document_index

fake_embeddings = DeterministicFakeEmbedding(size=settings.EMBEDDING_DIM)


class DocumentIndexTests(TestCase):
    @mock.patch("apps.rag.services.indexing.embeddings_get", return_value=fake_embeddings)
    def test_index_creates_chunks_and_marks_ready(self, _):
        document = DocumentFactory(status=Document.Status.PENDING)

        document = document_index(document=document)

        self.assertEqual(document.status, Document.Status.READY)
        self.assertEqual(document.error, "")
        self.assertIsNotNone(document.indexed_at)
        self.assertEqual(document.embedding_model, f"{settings.EMBEDDING_PROVIDER}:{settings.EMBEDDING_MODEL}")

        chunks = list(Chunk.objects.filter(document=document).order_by("index"))
        self.assertEqual(len(chunks), document.chunk_count)
        self.assertEqual([c.index for c in chunks], list(range(len(chunks))))
        self.assertEqual(len(chunks[0].embedding), settings.EMBEDDING_DIM)
        self.assertEqual(chunks[0].char_count, len(chunks[0].text))
        self.assertEqual(chunks[0].metadata["h1"], "Notes")

    @mock.patch("apps.rag.services.indexing.embeddings_get", return_value=fake_embeddings)
    def test_reindex_replaces_previous_chunks(self, _):
        document = DocumentFactory()
        stale = ChunkFactory(document=document, index=99, text="stale")

        document = document_index(document=document)

        self.assertFalse(Chunk.objects.filter(id=stale.id).exists())
        self.assertEqual(Chunk.objects.filter(document=document).count(), document.chunk_count)

    @mock.patch("apps.rag.services.indexing.embeddings_get", side_effect=RuntimeError("model download failed"))
    def test_failure_is_recorded_not_raised(self, _):
        document = DocumentFactory(status=Document.Status.PENDING)

        document = document_index(document=document)

        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn("model download failed", document.error)
        self.assertEqual(Chunk.objects.filter(document=document).count(), 0)
