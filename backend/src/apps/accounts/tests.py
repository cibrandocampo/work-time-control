"""Tests for accounts models and views."""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import User


@pytest.mark.django_db
class TestUserModel:
    """Tests for the User model."""

    def test_create_user(self):
        """Can create a user."""
        user = User.objects.create_user(
            username="newuser",
            email="new@example.com",
            password="pass123"
        )
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.check_password("pass123")

    def test_user_locations_many_to_many(self, user, location):
        """User can have multiple locations."""
        user.locations.add(location)
        assert location in user.locations.all()

    def test_location_users_reverse_relation(self, user, location):
        """Locations have reverse relation to users."""
        user.locations.add(location)
        assert user in location.users.all()


@pytest.mark.django_db
class TestMeView:
    """Tests for the /me/ endpoint."""

    def test_get_me_requires_auth(self, api_client):
        """GET /me/ requires authentication."""
        response = api_client.get(reverse("me"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me(self, authenticated_client, user):
        """GET /me/ returns current user."""
        response = authenticated_client.get(reverse("me"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "testuser"
        assert response.data["email"] == "test@example.com"

    def test_get_me_includes_locations(self, authenticated_client, user, location):
        """GET /me/ includes user's locations."""
        user.locations.add(location)
        response = authenticated_client.get(reverse("me"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["locations"]) == 1
        assert response.data["locations"][0]["name"] == "Madrid HQ"

    def test_patch_me(self, authenticated_client, user):
        """PATCH /me/ updates user fields."""
        response = authenticated_client.patch(
            reverse("me"),
            {"first_name": "Test", "last_name": "User"},
            format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Test"
        assert response.data["last_name"] == "User"

        user.refresh_from_db()
        assert user.first_name == "Test"


@pytest.mark.django_db
class TestChangePasswordView:
    """Tests for password change endpoint."""

    def test_change_password_requires_auth(self, api_client):
        """Change password requires authentication."""
        response = api_client.post(reverse("change-password"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_change_password_success(self, authenticated_client, user):
        """Can change password with correct current password."""
        response = authenticated_client.post(
            reverse("change-password"),
            {
                "current_password": "testpass123",
                "new_password": "newpass456"
            },
            format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

        user.refresh_from_db()
        assert user.check_password("newpass456")

    def test_change_password_wrong_current(self, authenticated_client, user):
        """Cannot change password with wrong current password."""
        response = authenticated_client.post(
            reverse("change-password"),
            {
                "current_password": "wrongpassword",
                "new_password": "newpass456"
            },
            format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        user.refresh_from_db()
        assert user.check_password("testpass123")

    def test_change_password_missing_fields(self, authenticated_client):
        """Change password requires both fields."""
        response = authenticated_client.post(
            reverse("change-password"),
            {"new_password": "newpass456"},
            format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAuthTokens:
    """Tests for JWT token endpoints."""

    def test_obtain_token(self, api_client, user):
        """Can obtain access token with correct credentials."""
        response = api_client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "testpass123"},
            format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_obtain_token_invalid_credentials(self, api_client, user):
        """Cannot obtain token with wrong password."""
        response = api_client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "wrongpass"},
            format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client, user):
        """Can refresh access token."""
        # First get tokens
        token_response = api_client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "testpass123"},
            format="json"
        )
        refresh_token = token_response.data["refresh"]

        # Refresh
        response = api_client.post(
            reverse("token_refresh"),
            {"refresh": refresh_token},
            format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_access_protected_endpoint_with_token(self, api_client, user):
        """Can access protected endpoints with valid token."""
        # Get token
        token_response = api_client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "testpass123"},
            format="json"
        )
        access_token = token_response.data["access"]

        # Access protected endpoint
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.get(reverse("me"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "testuser"
