"""Pytest fixtures for the WTC backend tests."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.companies.models import Company, Location
from apps.core.models import DayType


User = get_user_model()


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def other_user(db):
    """Create and return another test user."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="otherpass123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an API client authenticated as the test user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def company(db):
    """Create and return a test company."""
    return Company.objects.create(name="Test Company")


@pytest.fixture
def location(db, company):
    """Create and return a test location."""
    return Location.objects.create(
        company=company,
        name="Madrid HQ",
        latitude=40.4168,
        longitude=-3.7038,
        default_daily_hours=8.0,
        default_rest_days=[5, 6],  # Saturday and Sunday
    )


@pytest.fixture
def remote_location(db, company):
    """Create and return a remote location."""
    return Location.objects.create(
        company=company,
        name="Remote",
        latitude=0,
        longitude=0,
        default_daily_hours=8.0,
    )


@pytest.fixture
def working_day_type(db):
    """Create and return a 'Working' day type."""
    day_type, _ = DayType.objects.get_or_create(
        name="Working",
        defaults={"requires_signing": True}
    )
    return day_type


@pytest.fixture
def vacation_day_type(db):
    """Create and return a 'Vacation' day type."""
    day_type, _ = DayType.objects.get_or_create(
        name="Vacation",
        defaults={"requires_signing": False}
    )
    return day_type


@pytest.fixture
def user_with_location(user, location):
    """Return a user with an assigned location."""
    user.locations.add(location)
    return user
