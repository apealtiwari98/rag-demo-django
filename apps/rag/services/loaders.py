"""
Stage 1 of indexing: LOAD.

Turn a stored file into LangChain `Document`s (plain text + metadata). One
`Document` per natural unit: a PDF gives one per page (so we can cite pages),
a text file gives one for the whole file.
"""

from io import BytesIO

from langchain_core.documents import Document as LCDocument
from pypdf import PdfReader

from apps.core.exceptions import ApplicationError
from apps.documents.models import Document

TEXT_MIME_TYPES = {"text/plain", "text/markdown", "text/csv", "application/json"}


def _load_text(*, raw: bytes) -> list[LCDocument]:
    text = raw.decode("utf-8", errors="replace")

    return [LCDocument(page_content=text, metadata={})]


def _load_pdf(*, raw: bytes) -> list[LCDocument]:
    reader = PdfReader(BytesIO(raw))
    docs: list[LCDocument] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            docs.append(LCDocument(page_content=text, metadata={"page": page_number}))

    return docs


def document_load(*, document: Document) -> list[LCDocument]:
    with document.file.open("rb") as fh:
        raw = fh.read()

    if document.mime_type == "application/pdf":
        docs = _load_pdf(raw=raw)
    elif document.mime_type in TEXT_MIME_TYPES:
        docs = _load_text(raw=raw)
    else:
        raise ApplicationError(f"No loader for mime type '{document.mime_type}'.")

    docs = [doc for doc in docs if doc.page_content.strip()]

    if not docs:
        raise ApplicationError(
            "No extractable text found in the file (scanned PDFs need OCR, which is not supported)."
        )

    for doc in docs:
        doc.metadata.setdefault("source", document.title)

    return docs
