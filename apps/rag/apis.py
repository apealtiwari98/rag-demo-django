from django.conf import settings
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import LimitOffsetPagination, get_paginated_response
from apps.core.serializers import inline_serializer
from apps.rag.models import QueryLog
from apps.rag.selectors import chunk_search
from apps.rag.services import question_answer


class RetrievalInputSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000)
    top_k = serializers.IntegerField(min_value=1, max_value=settings.TOP_K_MAX, default=settings.TOP_K)
    document_ids = serializers.ListField(child=serializers.UUIDField(), required=False)


class ChunkSearchApi(APIView):
    """
    Retrieval only — no LLM. Use it to see which passages a question pulls
    back (and how similar they are) before trusting an answer built on them.
    """

    InputSerializer = RetrievalInputSerializer

    class OutputSerializer(serializers.Serializer):
        score = serializers.FloatField()
        chunk = inline_serializer(
            name="ChunkSearchHit",
            fields={
                "id": serializers.UUIDField(),
                "document_id": serializers.UUIDField(),
                "document_title": serializers.CharField(source="document.title"),
                "index": serializers.IntegerField(),
                "text": serializers.CharField(),
                "metadata": serializers.JSONField(),
            },
        )

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        hits = chunk_search(user=request.user, **serializer.validated_data)

        return Response(self.OutputSerializer(hits, many=True).data)


class QuestionAnswerApi(APIView):
    InputSerializer = RetrievalInputSerializer

    class OutputSerializer(serializers.Serializer):
        id = serializers.UUIDField()
        question = serializers.CharField()
        answer = serializers.CharField()
        sources = serializers.JSONField()
        llm_model = serializers.CharField()
        embedding_model = serializers.CharField()
        latency_ms = serializers.IntegerField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query_log = question_answer(user=request.user, **serializer.validated_data)

        return Response(self.OutputSerializer(query_log).data)


class QueryLogListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 20

    OutputSerializer = QuestionAnswerApi.OutputSerializer

    def get(self, request):
        queries = QueryLog.objects.filter(user=request.user)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=queries,
            request=request,
            view=self,
        )
