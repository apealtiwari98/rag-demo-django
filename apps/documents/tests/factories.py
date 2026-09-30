import factory
from django.conf import settings

from apps.documents.models import Chunk, Document
from apps.users.tests.factories import UserFactory

MARKDOWN_FIXTURE = b"# Notes\n\nDocumento indexes uploaded files.\n\n## Details\n\nChunks live in Postgres.\n"


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Document

    owner = factory.SubFactory(UserFactory)
    file = factory.django.FileField(filename="notes.md", data=MARKDOWN_FIXTURE)
    title = "notes.md"
    mime_type = "text/markdown"
    size = len(MARKDOWN_FIXTURE)
    status = Document.Status.READY


def zero_vector() -> list[float]:
    return [0.0] * settings.EMBEDDING_DIM


def unit_vector(axis: int) -> list[float]:
    """Basis vector e_axis: handy for exact cosine similarity in tests."""
    vector = zero_vector()
    vector[axis] = 1.0
    return vector


class ChunkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Chunk

    document = factory.SubFactory(DocumentFactory)
    index = factory.Sequence(lambda n: n)
    text = factory.Sequence(lambda n: f"chunk number {n}")
    char_count = factory.LazyAttribute(lambda obj: len(obj.text))
    metadata = factory.LazyFunction(dict)
    embedding = factory.LazyFunction(zero_vector)
