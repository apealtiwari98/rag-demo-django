from unittest import mock

from django.test import TestCase
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from apps.documents.tests.factories import ChunkFactory, DocumentFactory, unit_vector
from apps.rag.models import QueryLog
from apps.rag.services import question_answer
from apps.rag.services.answering import NO_CONTEXT_ANSWER, context_format
from apps.rag.tests.selectors.test_chunk_search import AxisEmbeddings
from apps.users.tests.factories import UserFactory


@mock.patch("apps.rag.selectors.embeddings_get", return_value=AxisEmbeddings(axis=0))
class QuestionAnswerTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.document = DocumentFactory(owner=self.user, title="notes.md")
        self.chunk = ChunkFactory(document=self.document, text="Chunks live in Postgres.", embedding=unit_vector(0))

    @mock.patch("apps.rag.services.answering.llm_get")
    def test_answer_is_generated_from_retrieved_context_and_logged(self, llm_get, _):
        llm_get.return_value = FakeListChatModel(responses=["They live in Postgres [1]."])

        query_log = question_answer(user=self.user, question="Where do chunks live?", top_k=3)

        self.assertEqual(query_log.answer, "They live in Postgres [1].")
        self.assertEqual(query_log.sources[0]["n"], 1)
        self.assertEqual(query_log.sources[0]["chunk_id"], str(self.chunk.id))
        self.assertEqual(query_log.sources[0]["document_title"], "notes.md")
        self.assertAlmostEqual(query_log.sources[0]["score"], 1.0, places=3)
        self.assertEqual(query_log.top_k, 3)
        self.assertEqual(QueryLog.objects.filter(user=self.user).count(), 1)

    @mock.patch("apps.rag.services.answering.llm_get")
    def test_no_retrieved_context_skips_the_llm(self, llm_get, _):
        other_user = UserFactory()

        query_log = question_answer(user=other_user, question="Where do chunks live?", top_k=3)

        self.assertEqual(query_log.answer, NO_CONTEXT_ANSWER)
        self.assertEqual(query_log.sources, [])
        llm_get.assert_not_called()

    def test_context_format_numbers_passages_with_location(self, _):
        from langchain_core.documents import Document as LCDocument

        docs = [LCDocument(page_content="body", metadata={"document_title": "a.pdf", "page": 3})]

        self.assertEqual(context_format(docs), "[1] (a.pdf, page 3)\nbody")
