from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import ChangePasswordView, MeView

# Add documentation to JWT views
TokenObtainPairView = extend_schema(
    tags=["Authentication"],
    summary="Obtain token pair",
    description="Authenticate with username and password to obtain access and refresh JWT tokens.",
)(TokenObtainPairView)
TokenRefreshView = extend_schema(
    tags=["Authentication"],
    summary="Refresh access token",
    description="Use a valid refresh token to obtain a new access token.",
)(TokenRefreshView)

urlpatterns = [
    # JWT Authentication
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # User profile
    path("me/", MeView.as_view(), name="me"),
    path("me/change-password/", ChangePasswordView.as_view(), name="change-password"),
]
