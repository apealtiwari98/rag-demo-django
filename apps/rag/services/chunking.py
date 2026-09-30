"""
Stage 2 of indexing: CHUNK.

Embedding models have a small input window and retrieval works best on
focused passages, so each loaded document is split into overlapping pieces.

Knobs (settings): CHUNK_SIZE (characters), CHUNK_OVERLAP (characters shared
between neighbours so a sentence cut in half still appears whole somewhere).
"""

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

MARKDOWN_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


def _split_markdown_by_headers(*, docs: list[LCDocument]) -> list[LCDocument]:
    """
    Pre-split markdown on headings so a chunk never straddles two sections and
    each chunk carries its heading path in metadata (useful for citations).
    """
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=MARKDOWN_HEADERS, strip_headers=False)
    sections: list[LCDocument] = []

    for doc in docs:
        for section in header_splitter.split_text(doc.page_content):
            section.metadata = {**doc.metadata, **section.metadata}
            sections.append(section)

    return sections


def text_chunk(
    *,
    docs: list[LCDocument],
    chunk_size: int,
    chunk_overlap: int,
    mime_type: str = "text/plain",
) -> list[LCDocument]:
    if mime_type == "text/markdown":
        docs = _split_markdown_by_headers(docs=docs)

    # Tries to split on paragraphs first, then lines, then sentences/words,
    # only falling back to a hard character cut when nothing else fits.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(docs)

    for position, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = position

    return chunks
