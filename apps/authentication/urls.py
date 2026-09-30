from django.urls import path

from apps.authentication.apis import TokenObtainApi, TokenRefreshApi

urlpatterns = [
    path("token/", TokenObtainApi.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshApi.as_view(), name="token-refresh"),
]
