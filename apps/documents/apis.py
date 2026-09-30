from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import LimitOffsetPagination, get_paginated_response
from apps.documents.models import Document
from apps.documents.selectors import chunk_list_for_document, document_get, document_list
from apps.documents.services import document_create, document_delete, document_reindex


class DocumentOutputSerializer(serializers.Serializer):
    """Shared shape for every document-returning API."""

    id = serializers.UUIDField()
    title = serializers.CharField()
    mime_type = serializers.CharField()
    size = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Document.Status.choices)
    error = serializers.CharField()
    chunk_count = serializers.IntegerField()
    embedding_model = serializers.CharField()
    indexed_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class DocumentCreateApi(APIView):
    parser_classes = [MultiPartParser, FormParser]

    class InputSerializer(serializers.Serializer):
        file = serializers.FileField()
        title = serializers.CharField(max_length=255, required=False)

    OutputSerializer = DocumentOutputSerializer

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document = document_create(owner=request.user, **serializer.validated_data)

        return Response(self.OutputSerializer(document).data, status=status.HTTP_201_CREATED)


class DocumentListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 20

    class FilterSerializer(serializers.Serializer):
        status = serializers.ChoiceField(choices=Document.Status.choices, required=False)
        mime_type = serializers.CharField(required=False)
        q = serializers.CharField(required=False)

    OutputSerializer = DocumentOutputSerializer

    def get(self, request):
        filters_serializer = self.FilterSerializer(data=request.query_params)
        filters_serializer.is_valid(raise_exception=True)

        documents = document_list(owner=request.user, filters=filters_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=documents,
            request=request,
            view=self,
        )


class DocumentDetailApi(APIView):
    OutputSerializer = DocumentOutputSerializer

    def get(self, request, document_id):
        document = document_get(owner=request.user, document_id=document_id)

        return Response(self.OutputSerializer(document).data)


class DocumentDeleteApi(APIView):
    def delete(self, request, document_id):
        document = document_get(owner=request.user, document_id=document_id)

        document_delete(document=document)

        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentReindexApi(APIView):
    OutputSerializer = DocumentOutputSerializer

    def post(self, request, document_id):
        document = document_get(owner=request.user, document_id=document_id)

        document = document_reindex(document=document)

        return Response(self.OutputSerializer(document).data)


class DocumentChunkListApi(APIView):
    """
    Learning aid: see exactly what the splitter produced for a document.
    """

    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 200

    class OutputSerializer(serializers.Serializer):
        id = serializers.UUIDField()
        index = serializers.IntegerField()
        text = serializers.CharField()
        char_count = serializers.IntegerField()
        metadata = serializers.JSONField()

    def get(self, request, document_id):
        chunks = chunk_list_for_document(owner=request.user, document_id=document_id)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=chunks,
            request=request,
            view=self,
        )
