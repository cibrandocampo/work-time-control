from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ChangePasswordSerializer, UserMeSerializer


class MeView(APIView):
    """Get or update current user profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User Profile"],
        summary="Get current user",
        description="Returns the profile of the authenticated user including location and company info.",
    )
    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        tags=["User Profile"],
        summary="Update current user",
        description="Update the authenticated user's profile fields.",
    )
    def patch(self, request):
        serializer = UserMeSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Change current user password."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User Profile"],
        summary="Change password",
        description="Change the current user's password. Requires current password for verification.",
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data["new_password"])
            request.user.save()
            return Response({"message": "Password changed successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
