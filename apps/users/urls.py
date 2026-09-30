from django.urls import path

from apps.users.apis import UserCreateApi, UserMeApi

urlpatterns = [
    path("", UserCreateApi.as_view(), name="create"),
    path("me/", UserMeApi.as_view(), name="me"),
]
