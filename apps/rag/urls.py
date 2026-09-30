from django.urls import path

from apps.rag.apis import ChunkSearchApi, QueryLogListApi, QuestionAnswerApi

urlpatterns = [
    path("search/", ChunkSearchApi.as_view(), name="search"),
    path("ask/", QuestionAnswerApi.as_view(), name="ask"),
    path("queries/", QueryLogListApi.as_view(), name="queries"),
]
