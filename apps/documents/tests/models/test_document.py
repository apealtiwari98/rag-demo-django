from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from apps.documents.models import Document
from apps.users.tests.factories import UserFactory


class DocumentTests(TestCase):
    def setUp(self):
        self.owner = UserFactory()

    def _document(self, **overrides) -> Document:
        fields = {
            "owner": self.owner,
            "file": ContentFile(b"hello", name="hello.txt"),
            "title": "hello.txt",
            "mime_type": "text/plain",
            "size": 5,
        }
        fields.update(overrides)
        return Document(**fields)

    def test_valid_document_passes_full_clean(self):
        self._document().full_clean()

    def test_unsupported_mime_type_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self._document(mime_type="application/x-msdownload").full_clean()

        self.assertIn("mime_type", ctx.exception.message_dict)

    @override_settings(DOCUMENT_MAX_SIZE_BYTES=10)
    def test_oversized_file_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self._document(size=11).full_clean()

        self.assertIn("size", ctx.exception.message_dict)
