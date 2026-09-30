from django.core.management.base import BaseCommand, CommandError

from apps.documents.models import Document
from apps.rag.services import document_index


class Command(BaseCommand):
    help = "Re-run the indexing pipeline. Needed after changing EMBEDDING_MODEL or CHUNK_* settings."

    def add_arguments(self, parser):
        parser.add_argument("--document", help="Only this document id")
        parser.add_argument("--owner", help="Only documents owned by this email")
        parser.add_argument("--failed", action="store_true", help="Only documents with status=failed")

    def handle(self, *args, **options):
        qs = Document.objects.all()

        if options["document"]:
            qs = qs.filter(id=options["document"])
        if options["owner"]:
            qs = qs.filter(owner__email=options["owner"])
        if options["failed"]:
            qs = qs.filter(status=Document.Status.FAILED)

        if not qs.exists():
            raise CommandError("No documents matched.")

        for document in qs.iterator():
            document = document_index(document=document)
            self.stdout.write(f"{document.id}  {document.status:<10} chunks={document.chunk_count}  {document.title}")
            if document.error:
                self.stderr.write(f"    {document.error}")
