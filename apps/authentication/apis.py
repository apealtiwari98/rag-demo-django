from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class TokenObtainApi(TokenObtainPairView):
    """POST {email, password} -> {access, refresh}"""


class TokenRefreshApi(TokenRefreshView):
    """POST {refresh} -> {access}"""
