from django.test import SimpleTestCase
from langchain_core.documents import Document as LCDocument

from apps.rag.services import text_chunk


class TextChunkTests(SimpleTestCase):
    def test_short_text_is_a_single_chunk(self):
        chunks = text_chunk(docs=[LCDocument(page_content="tiny")], chunk_size=100, chunk_overlap=10)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].metadata["chunk_index"], 0)

    def test_long_text_is_split_with_overlap(self):
        sentences = " ".join(f"Sentence number {i} is here." for i in range(40))

        chunks = text_chunk(docs=[LCDocument(page_content=sentences)], chunk_size=120, chunk_overlap=30)

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.page_content), 120)
        # Overlap: the tail of one chunk reappears at the head of the next.
        tail = chunks[0].page_content[-20:]
        self.assertIn(tail.split(" ")[-1], chunks[1].page_content)
        self.assertEqual([c.metadata["chunk_index"] for c in chunks], list(range(len(chunks))))

    def test_markdown_chunks_carry_heading_path_and_source_metadata(self):
        markdown = "# Guide\n\nIntro text.\n\n## Install\n\nRun the installer.\n"
        docs = [LCDocument(page_content=markdown, metadata={"source": "guide.md"})]

        chunks = text_chunk(docs=docs, chunk_size=500, chunk_overlap=0, mime_type="text/markdown")

        install = next(c for c in chunks if "installer" in c.page_content)
        self.assertEqual(install.metadata["h1"], "Guide")
        self.assertEqual(install.metadata["h2"], "Install")
        self.assertEqual(install.metadata["source"], "guide.md")

    def test_page_metadata_is_preserved(self):
        docs = [LCDocument(page_content="page one text", metadata={"page": 1})]

        chunks = text_chunk(docs=docs, chunk_size=100, chunk_overlap=0)

        self.assertEqual(chunks[0].metadata["page"], 1)
