from unittest import mock

from django.test import TestCase
from langchain_core.embeddings import Embeddings

from apps.documents.models import Document
from apps.documents.tests.factories import ChunkFactory, DocumentFactory, unit_vector
from apps.rag.selectors import chunk_search
from apps.users.tests.factories import UserFactory


class AxisEmbeddings(Embeddings):
    """Every query embeds to the same basis vector, so scores are exact."""

    def __init__(self, axis: int):
        self.axis = axis

    def embed_documents(self, texts):
        return [unit_vector(self.axis) for _ in texts]

    def embed_query(self, text):
        return unit_vector(self.axis)


@mock.patch("apps.rag.selectors.embeddings_get", return_value=AxisEmbeddings(axis=0))
class ChunkSearchTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.document = DocumentFactory(owner=self.user)

        self.exact = ChunkFactory(document=self.document, text="same direction", embedding=unit_vector(0))
        self.orthogonal = ChunkFactory(document=self.document, text="unrelated", embedding=unit_vector(1))

        # Must never surface: someone else's chunk, and a chunk of a failed document.
        ChunkFactory(document=DocumentFactory(), embedding=unit_vector(0))
        ChunkFactory(document=DocumentFactory(owner=self.user, status=Document.Status.FAILED), embedding=unit_vector(0))

    def test_orders_by_cosine_similarity_and_scopes_to_owner(self, _):
        hits = chunk_search(user=self.user, question="anything", top_k=10)

        self.assertEqual([hit.chunk.id for hit in hits], [self.exact.id, self.orthogonal.id])
        self.assertAlmostEqual(hits[0].score, 1.0, places=5)
        self.assertAlmostEqual(hits[1].score, 0.0, places=5)

    def test_top_k_limits_results(self, _):
        hits = chunk_search(user=self.user, question="anything", top_k=1)

        self.assertEqual([hit.chunk.id for hit in hits], [self.exact.id])

    def test_document_ids_filter(self, _):
        other_document = DocumentFactory(owner=self.user)
        only = ChunkFactory(document=other_document, embedding=unit_vector(0))

        hits = chunk_search(user=self.user, question="anything", top_k=10, document_ids=[other_document.id])

        self.assertEqual([hit.chunk.id for hit in hits], [only.id])
