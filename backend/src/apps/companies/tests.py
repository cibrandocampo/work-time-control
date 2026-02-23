"""Tests for companies models and views."""
import pytest
from datetime import date
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status

from apps.companies.models import Company, Location, BankHoliday


@pytest.mark.django_db
class TestCompanyModel:
    """Tests for the Company model."""

    def test_create_company(self):
        """Can create a company."""
        company = Company.objects.create(name="Test Company")
        assert company.name == "Test Company"

    def test_str_representation(self, company):
        """String representation is the name."""
        assert str(company) == "Test Company"


@pytest.mark.django_db
class TestLocationModel:
    """Tests for the Location model."""

    def test_create_location(self, company):
        """Can create a location with required fields."""
        location = Location.objects.create(
            company=company,
            name="Barcelona Office",
            latitude=41.3851,
            longitude=2.1734
        )
        assert location.name == "Barcelona Office"
        assert location.company == company
        assert float(location.latitude) == 41.3851
        assert float(location.longitude) == 2.1734

    def test_default_daily_hours(self, company):
        """Default daily hours is 8.0."""
        location = Location.objects.create(
            company=company,
            name="Test",
            latitude=0,
            longitude=0
        )
        assert location.default_daily_hours == 8.0

    def test_default_rest_days_on_save(self, company):
        """Rest days default to Saturday and Sunday on save."""
        location = Location.objects.create(
            company=company,
            name="Test",
            latitude=0,
            longitude=0
        )
        # The save method sets default rest days
        assert location.default_rest_days == [5, 6]

    def test_custom_rest_days(self, company):
        """Can set custom rest days."""
        location = Location.objects.create(
            company=company,
            name="Test",
            latitude=0,
            longitude=0,
            default_rest_days=[4, 5]  # Friday, Saturday
        )
        assert location.default_rest_days == [4, 5]

    def test_str_representation(self, location):
        """String representation includes name and company."""
        assert "Madrid HQ" in str(location)
        assert "Test Company" in str(location)


@pytest.mark.django_db
class TestBankHolidayModel:
    """Tests for the BankHoliday model."""

    def test_create_bank_holiday(self, location):
        """Can create a bank holiday."""
        holiday = BankHoliday.objects.create(
            location=location,
            date=date(2026, 12, 25),
            name="Christmas"
        )
        assert holiday.name == "Christmas"
        assert holiday.date == date(2026, 12, 25)
        assert holiday.location == location

    def test_unique_together(self, location):
        """Same date cannot have two holidays at same location."""
        BankHoliday.objects.create(
            location=location,
            date=date(2026, 1, 1),
            name="New Year"
        )
        with pytest.raises(IntegrityError):
            BankHoliday.objects.create(
                location=location,
                date=date(2026, 1, 1),
                name="Another Holiday"
            )

    def test_str_representation(self, location):
        """String representation includes name and date."""
        holiday = BankHoliday.objects.create(
            location=location,
            date=date(2026, 5, 1),
            name="Labor Day"
        )
        assert "Labor Day" in str(holiday)
        assert "2026-05-01" in str(holiday)


@pytest.mark.django_db
class TestLocationViewSet:
    """Tests for Location API endpoints."""

    def test_list_locations_requires_auth(self, api_client):
        """List locations requires authentication."""
        response = api_client.get(reverse("location-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_locations(self, api_client, user_with_location, location):
        """Can list locations for user's companies."""
        api_client.force_authenticate(user=user_with_location)
        response = api_client.get(reverse("location-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Madrid HQ"

    def test_retrieve_location(self, api_client, user_with_location, location):
        """Can retrieve a single location."""
        api_client.force_authenticate(user=user_with_location)
        response = api_client.get(
            reverse("location-detail", args=[location.id])
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Madrid HQ"
        assert "latitude" in response.data
        assert "longitude" in response.data

    def test_create_location(self, authenticated_client, company):
        """Can create a location."""
        data = {
            "company": company.id,
            "name": "New Office",
            "latitude": 40.0,
            "longitude": -3.0
        }
        response = authenticated_client.post(
            reverse("location-list"),
            data,
            format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Office"

    def test_update_location(self, api_client, user_with_location, location):
        """Can update a location."""
        api_client.force_authenticate(user=user_with_location)
        response = api_client.patch(
            reverse("location-detail", args=[location.id]),
            {"name": "Updated HQ"},
            format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated HQ"

    def test_delete_location(self, api_client, user_with_location, location):
        """Can delete a location."""
        api_client.force_authenticate(user=user_with_location)
        response = api_client.delete(
            reverse("location-detail", args=[location.id])
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Location.objects.filter(id=location.id).exists()


@pytest.mark.django_db
class TestBankHolidayViewSet:
    """Tests for BankHoliday API endpoints."""

    def test_list_bank_holidays(self, api_client, user_with_location, location):
        """Can list bank holidays for user's locations."""
        api_client.force_authenticate(user=user_with_location)
        BankHoliday.objects.create(
            location=location,
            date=date(2026, 12, 25),
            name="Christmas"
        )
        response = api_client.get(reverse("bankholiday-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_create_bank_holiday(self, authenticated_client, location):
        """Can create a bank holiday."""
        data = {
            "location": location.id,
            "date": "2026-01-06",
            "name": "Epiphany"
        }
        response = authenticated_client.post(
            reverse("bankholiday-list"),
            data,
            format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Epiphany"
