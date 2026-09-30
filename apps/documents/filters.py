import django_filters

from apps.documents.models import Document


class DocumentFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = Document
        fields = ("status", "mime_type", "q")
