from unittest import mock

from django.urls import reverse
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from rest_framework.test import APIClient, APITestCase

from apps.documents.tests.factories import ChunkFactory, DocumentFactory, unit_vector
from apps.rag.tests.selectors.test_chunk_search import AxisEmbeddings
from apps.users.tests.factories import UserFactory


@mock.patch("apps.rag.selectors.embeddings_get", return_value=AxisEmbeddings(axis=0))
class RagApisTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        document = DocumentFactory(owner=self.user, title="notes.md")
        self.chunk = ChunkFactory(document=document, text="Chunks live in Postgres.", embedding=unit_vector(0))

    def test_search_returns_hits_with_scores(self, _):
        response = self.client.post(reverse("api_v1:rag:search"), {"question": "where?"}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertAlmostEqual(response.data[0]["score"], 1.0, places=3)
        self.assertEqual(response.data[0]["chunk"]["text"], "Chunks live in Postgres.")
        self.assertEqual(response.data[0]["chunk"]["document_title"], "notes.md")

    def test_search_validates_top_k(self, _):
        response = self.client.post(reverse("api_v1:rag:search"), {"question": "?", "top_k": 999}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("top_k", response.data["extra"]["fields"])

    @mock.patch("apps.rag.services.answering.llm_get", return_value=FakeListChatModel(responses=["Postgres [1]."]))
    def test_ask_returns_answer_and_sources_and_is_listed_in_queries(self, *_):
        response = self.client.post(reverse("api_v1:rag:ask"), {"question": "where?"}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["answer"], "Postgres [1].")
        self.assertEqual(response.data["sources"][0]["chunk_id"], str(self.chunk.id))

        response = self.client.get(reverse("api_v1:rag:queries"))

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["question"], "where?")
