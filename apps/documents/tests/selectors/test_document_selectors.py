from django.http import Http404
from django.test import TestCase

from apps.documents.models import Document
from apps.documents.selectors import chunk_list_for_document, document_get, document_list
from apps.documents.tests.factories import ChunkFactory, DocumentFactory
from apps.users.tests.factories import UserFactory


class DocumentSelectorsTests(TestCase):
    def setUp(self):
        self.owner = UserFactory()
        self.other = UserFactory()
        self.mine = DocumentFactory(owner=self.owner, title="mine.md")
        self.mine_failed = DocumentFactory(owner=self.owner, title="broken.md", status=Document.Status.FAILED)
        self.theirs = DocumentFactory(owner=self.other, title="theirs.md")

    def test_document_list_is_scoped_to_owner(self):
        ids = set(document_list(owner=self.owner).values_list("id", flat=True))

        self.assertEqual(ids, {self.mine.id, self.mine_failed.id})

    def test_document_list_applies_filters(self):
        documents = document_list(owner=self.owner, filters={"status": Document.Status.FAILED})
        self.assertEqual(list(documents), [self.mine_failed])

        documents = document_list(owner=self.owner, filters={"q": "MINE"})
        self.assertEqual(list(documents), [self.mine])

    def test_document_get_returns_own_document(self):
        self.assertEqual(document_get(owner=self.owner, document_id=self.mine.id), self.mine)

    def test_document_get_hides_other_users_documents(self):
        with self.assertRaises(Http404):
            document_get(owner=self.owner, document_id=self.theirs.id)

    def test_chunk_list_for_document_is_ordered_by_index(self):
        ChunkFactory(document=self.mine, index=1)
        ChunkFactory(document=self.mine, index=0)
        ChunkFactory(document=self.theirs, index=0)

        chunks = chunk_list_for_document(owner=self.owner, document_id=self.mine.id)

        self.assertEqual([c.index for c in chunks], [0, 1])
