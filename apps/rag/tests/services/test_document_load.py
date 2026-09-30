from io import BytesIO

from django.core.files.base import ContentFile
from django.test import TestCase
from pypdf import PdfWriter

from apps.core.exceptions import ApplicationError
from apps.documents.tests.factories import DocumentFactory
from apps.rag.services import document_load


class DocumentLoadTests(TestCase):
    def test_text_file_loads_as_single_document_with_source(self):
        document = DocumentFactory(title="notes.md")

        docs = document_load(document=document)

        self.assertEqual(len(docs), 1)
        self.assertIn("Documento indexes", docs[0].page_content)
        self.assertEqual(docs[0].metadata["source"], "notes.md")

    def test_pdf_without_text_raises_application_error(self):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        buffer = BytesIO()
        writer.write(buffer)
        document = DocumentFactory(
            file=ContentFile(buffer.getvalue(), name="blank.pdf"),
            mime_type="application/pdf",
            title="blank.pdf",
        )

        with self.assertRaises(ApplicationError) as ctx:
            document_load(document=document)

        self.assertIn("No extractable text", ctx.exception.message)

    def test_empty_text_file_raises_application_error(self):
        document = DocumentFactory(file=ContentFile(b"   \n", name="empty.txt"), mime_type="text/plain")

        with self.assertRaises(ApplicationError):
            document_load(document=document)
