from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.services import user_create


class UserCreateApi(APIView):
    """
    Open sign-up. Fine for a learning project; gate it before exposing publicly.
    """

    permission_classes = [AllowAny]

    class InputSerializer(serializers.Serializer):
        email = serializers.EmailField()
        password = serializers.CharField(min_length=8, write_only=True)

    class OutputSerializer(serializers.Serializer):
        id = serializers.UUIDField()
        email = serializers.EmailField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = user_create(**serializer.validated_data)

        return Response(self.OutputSerializer(user).data, status=status.HTTP_201_CREATED)


class UserMeApi(APIView):
    class OutputSerializer(serializers.Serializer):
        id = serializers.UUIDField()
        email = serializers.EmailField()
        is_admin = serializers.BooleanField()
        created_at = serializers.DateTimeField()

    def get(self, request):
        return Response(self.OutputSerializer(request.user).data)
