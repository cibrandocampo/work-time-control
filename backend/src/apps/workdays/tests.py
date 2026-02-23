import io
import pytest
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company, Location
from apps.core.models import DayType

from .models import Signing, WorkDay


User = get_user_model()


# ==================== MODEL TESTS ====================


@pytest.mark.django_db
class TestWorkDayModel:
    """Tests for the WorkDay model."""

    def test_create_workday(self, user, location, working_day_type):
        """Can create a work day."""
        workday = WorkDay.objects.create(
            date=date(2026, 2, 8),
            employee=user,
            location=location,
            day_type=working_day_type
        )
        assert workday.date == date(2026, 2, 8)
        assert workday.employee == user
        assert workday.location == location

    def test_get_expected_hours_override(self, user, location, working_day_type):
        """expected_hours override takes precedence."""
        workday = WorkDay.objects.create(
            date=date(2026, 2, 8),
            employee=user,
            location=location,
            day_type=working_day_type,
            expected_hours=6.5
        )
        assert workday.get_expected_hours() == 6.5

    def test_get_expected_hours_from_location(self, user, location, working_day_type):
        """Falls back to location default hours."""
        workday = WorkDay.objects.create(
            date=date(2026, 2, 8),
            employee=user,
            location=location,
            day_type=working_day_type
        )
        assert workday.get_expected_hours() == 8.0

    def test_get_expected_hours_non_signing_day(self, user, location, vacation_day_type):
        """Non-signing day types return 0 hours."""
        workday = WorkDay.objects.create(
            date=date(2026, 2, 8),
            employee=user,
            location=location,
            day_type=vacation_day_type
        )
        assert workday.get_expected_hours() == 0.0

    def test_str_representation(self, user, location, working_day_type):
        """String representation includes key info."""
        workday = WorkDay.objects.create(
            date=date(2026, 2, 8),
            employee=user,
            location=location,
            day_type=working_day_type
        )
        s = str(workday)
        assert "2026-02-08" in s
        assert "Madrid HQ" in s

    def test_unique_together_constraint(self, user, location, working_day_type):
        """Cannot have duplicate workday for same date/user/location."""
        WorkDay.objects.create(
            date=date(2026, 2, 8),
            employee=user,
            location=location,
            day_type=working_day_type
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            WorkDay.objects.create(
                date=date(2026, 2, 8),
                employee=user,
                location=location,
                day_type=working_day_type
            )


@pytest.mark.django_db
class TestSigningModel:
    """Tests for the Signing model."""

    def test_create_signing(self, user, location):
        """Can create a signing."""
        now = timezone.now()
        signing = Signing.objects.create(
            employee=user,
            start_time=now,
            location=location
        )
        assert signing.employee == user
        assert signing.location == location
        assert signing.end_time is None

    def test_duration_returns_none_for_open_signing(self, user):
        """Duration is None for open signing."""
        signing = Signing.objects.create(
            employee=user,
            start_time=timezone.now()
        )
        assert signing.duration is None
        assert signing.duration_minutes is None

    def test_duration_calculation(self, user):
        """Duration is calculated correctly."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        end = timezone.make_aware(timezone.datetime(2026, 2, 8, 18, 30))
        signing = Signing.objects.create(
            employee=user,
            start_time=start,
            end_time=end
        )
        assert signing.duration == 9.5
        assert signing.duration_minutes == 570

    def test_str_representation(self, user):
        """String representation includes key info."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        signing = Signing.objects.create(
            employee=user,
            start_time=start
        )
        s = str(signing)
        assert "2026-02-08" in s

    def test_ordering(self, user):
        """Signings are ordered by start_time ascending (chronological)."""
        start1 = timezone.make_aware(timezone.datetime(2026, 2, 7, 9, 0))
        start2 = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        Signing.objects.create(employee=user, start_time=start1)
        Signing.objects.create(employee=user, start_time=start2)

        signings = list(Signing.objects.filter(employee=user))
        assert signings[0].start_time < signings[1].start_time


# ==================== VIEWSET TESTS ====================


@pytest.mark.django_db
class TestSigningViewSet:
    """Tests for Signing API endpoints."""

    def test_list_signings_requires_auth(self, api_client):
        """List signings requires authentication."""
        response = api_client.get(reverse("signing-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_signings(self, authenticated_client, user):
        """Can list user's signings."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        Signing.objects.create(employee=user, start_time=start)

        response = authenticated_client.get(reverse("signing-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_list_signings_filter_by_date(self, authenticated_client, user):
        """Can filter signings by date range."""
        start1 = timezone.make_aware(timezone.datetime(2026, 2, 1, 9, 0))
        start2 = timezone.make_aware(timezone.datetime(2026, 2, 15, 9, 0))
        Signing.objects.create(employee=user, start_time=start1)
        Signing.objects.create(employee=user, start_time=start2)

        response = authenticated_client.get(
            reverse("signing-list"),
            {"start_date": "2026-02-10", "end_date": "2026-02-20"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_list_signings_only_own(self, authenticated_client, user, other_user):
        """Only shows user's own signings."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        Signing.objects.create(employee=user, start_time=start)
        Signing.objects.create(employee=other_user, start_time=start)

        response = authenticated_client.get(reverse("signing-list"))
        assert len(response.data) == 1

    def test_create_signing(self, authenticated_client, user, location):
        """Can create a signing (check-in)."""
        response = authenticated_client.post(
            reverse("signing-list"),
            {
                "start_time": "2026-02-08T09:00:00Z",
                "location": location.id
            },
            format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Signing.objects.filter(employee=user).count() == 1

    def test_create_signing_auto_creates_workday(self, authenticated_client, user, location, working_day_type):
        """Creating signing auto-creates WorkDay."""
        response = authenticated_client.post(
            reverse("signing-list"),
            {
                "start_time": "2026-02-08T09:00:00Z",
                "location": location.id
            },
            format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED

        workday = WorkDay.objects.filter(
            employee=user,
            date=date(2026, 2, 8),
            location=location
        ).first()
        assert workday is not None

    def test_active_signing(self, authenticated_client, user):
        """Can get active signing."""
        start = timezone.now()
        Signing.objects.create(employee=user, start_time=start)

        response = authenticated_client.get(reverse("signing-active"))
        assert response.status_code == status.HTTP_200_OK
        assert "start_time" in response.data

    def test_active_signing_none(self, authenticated_client, user):
        """Returns null when no active signing."""
        response = authenticated_client.get(reverse("signing-active"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["active"] is None

    def test_checkout_signing(self, authenticated_client, user):
        """Can checkout an active signing."""
        start = timezone.now() - timedelta(hours=8)
        signing = Signing.objects.create(employee=user, start_time=start)

        response = authenticated_client.post(
            reverse("signing-checkout", args=[signing.id]),
            format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        signing.refresh_from_db()
        assert signing.end_time is not None

    def test_checkout_signing_custom_time(self, authenticated_client, user):
        """Can checkout with custom end time."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        signing = Signing.objects.create(employee=user, start_time=start)

        response = authenticated_client.post(
            reverse("signing-checkout", args=[signing.id]),
            {"end_time": "2026-02-08T18:00:00Z"},
            format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        signing.refresh_from_db()
        assert signing.duration_minutes == 540

    def test_checkout_already_ended(self, authenticated_client, user):
        """Cannot checkout already ended signing."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        end = timezone.make_aware(timezone.datetime(2026, 2, 8, 18, 0))
        signing = Signing.objects.create(
            employee=user,
            start_time=start,
            end_time=end
        )

        response = authenticated_client.post(
            reverse("signing-checkout", args=[signing.id]),
            format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already ended" in response.data["error"]

    def test_update_signing(self, authenticated_client, user):
        """Can update signing description."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        signing = Signing.objects.create(employee=user, start_time=start)

        response = authenticated_client.patch(
            reverse("signing-detail", args=[signing.id]),
            {"description": "Updated description"},
            format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        signing.refresh_from_db()
        assert signing.description == "Updated description"

    def test_delete_signing(self, authenticated_client, user):
        """Can delete a signing."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        signing = Signing.objects.create(employee=user, start_time=start)

        response = authenticated_client.delete(
            reverse("signing-detail", args=[signing.id])
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Signing.objects.filter(id=signing.id).exists()


@pytest.mark.django_db
class TestDaySummaryView:
    """Tests for the day summary endpoint."""

    def test_day_summary_requires_auth(self, api_client):
        """Day summary requires authentication."""
        response = api_client.get(reverse("day-summary-today"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_day_summary_today(self, authenticated_client, user):
        """Can get today's summary."""
        today = date.today()
        start = timezone.make_aware(timezone.datetime(
            today.year, today.month, today.day, 9, 0
        ))
        end = timezone.make_aware(timezone.datetime(
            today.year, today.month, today.day, 13, 0
        ))
        Signing.objects.create(employee=user, start_time=start, end_time=end)

        response = authenticated_client.get(reverse("day-summary-today"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_worked_minutes"] == 240
        assert response.data["expected_minutes"] == 480

    def test_day_summary_specific_date(self, authenticated_client, user):
        """Can get summary for a specific date."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        end = timezone.make_aware(timezone.datetime(2026, 2, 8, 18, 0))
        Signing.objects.create(employee=user, start_time=start, end_time=end)

        response = authenticated_client.get(
            reverse("day-summary", args=["2026-02-08"])
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_worked_minutes"] == 540

    def test_day_summary_overtime_positive(self, authenticated_client, user):
        """Overtime is positive when worked > expected."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 7, 0))
        end = timezone.make_aware(timezone.datetime(2026, 2, 8, 18, 0))
        Signing.objects.create(employee=user, start_time=start, end_time=end)

        response = authenticated_client.get(
            reverse("day-summary", args=["2026-02-08"])
        )
        assert response.data["overtime_minutes"] == 180  # 11h - 8h = 3h

    def test_day_summary_overtime_negative(self, authenticated_client, user):
        """Overtime is negative when worked < expected."""
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        end = timezone.make_aware(timezone.datetime(2026, 2, 8, 13, 0))
        Signing.objects.create(employee=user, start_time=start, end_time=end)

        response = authenticated_client.get(
            reverse("day-summary", args=["2026-02-08"])
        )
        assert response.data["overtime_minutes"] == -240  # 4h - 8h = -4h

    def test_day_summary_uses_workday_expected(self, authenticated_client, user, location, working_day_type):
        """Uses expected hours from WorkDay if exists."""
        WorkDay.objects.create(
            date=date(2026, 2, 8),
            employee=user,
            location=location,
            day_type=working_day_type,
            expected_hours=6.0
        )
        start = timezone.make_aware(timezone.datetime(2026, 2, 8, 9, 0))
        end = timezone.make_aware(timezone.datetime(2026, 2, 8, 15, 0))
        Signing.objects.create(employee=user, start_time=start, end_time=end)

        response = authenticated_client.get(
            reverse("day-summary", args=["2026-02-08"])
        )
        assert response.data["expected_minutes"] == 360  # 6 hours


@pytest.mark.django_db
class TestPeriodSummaryView:
    """Tests for the period summary endpoint."""

    def test_period_summary_month(self, authenticated_client, user):
        """Can get monthly summary."""
        # Create signings for multiple days
        for day in [1, 2, 3]:
            start = timezone.make_aware(timezone.datetime(2026, 2, day, 9, 0))
            end = timezone.make_aware(timezone.datetime(2026, 2, day, 17, 0))
            Signing.objects.create(employee=user, start_time=start, end_time=end)

        response = authenticated_client.get(
            reverse("period-summary"),
            {"period": "month", "year": 2026, "month": 2}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_worked_minutes"] == 1440  # 3 days * 8h
        assert response.data["days_worked"] == 3

    def test_period_summary_year(self, authenticated_client, user):
        """Can get yearly summary."""
        # Create signings for multiple months
        for month in [1, 2, 3]:
            start = timezone.make_aware(timezone.datetime(2026, month, 15, 9, 0))
            end = timezone.make_aware(timezone.datetime(2026, month, 15, 17, 0))
            Signing.objects.create(employee=user, start_time=start, end_time=end)

        response = authenticated_client.get(
            reverse("period-summary"),
            {"period": "year", "year": 2026}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["days_worked"] == 3


class ImportExportTestCase(APITestCase):
    """Tests for CSV import/export endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.company = Company.objects.create(name="Test Company")
        self.location = Location.objects.create(
            company=self.company,
            name="Madrid HQ",
            latitude=40.4168,
            longitude=-3.7038,
        )
        self.day_type = DayType.objects.create(
            name="Working",
            requires_signing=True,
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    # ==================== EXPORT TESTS ====================

    def test_export_requires_authentication(self):
        """Export endpoint requires authentication."""
        self.client.force_authenticate(user=None)
        url = reverse("signing-export")
        response = self.client.get(url, {"start_date": "2026-01-01", "end_date": "2026-01-31"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_export_requires_dates(self):
        """Export requires both start_date and end_date."""
        url = reverse("signing-export")

        # No dates
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

        # Only start_date
        response = self.client.get(url, {"start_date": "2026-01-01"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Only end_date
        response = self.client.get(url, {"end_date": "2026-01-31"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_export_invalid_date_format(self):
        """Export rejects invalid date formats."""
        url = reverse("signing-export")
        response = self.client.get(url, {"start_date": "invalid", "end_date": "2026-01-31"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid date format", response.json()["error"])

    def test_export_start_after_end(self):
        """Export rejects start_date after end_date."""
        url = reverse("signing-export")
        response = self.client.get(url, {"start_date": "2026-02-01", "end_date": "2026-01-01"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date must be before", response.json()["error"])

    def test_export_empty_csv(self):
        """Export returns CSV with headers when no signings exist."""
        url = reverse("signing-export")
        response = self.client.get(url, {"start_date": "2026-01-01", "end_date": "2026-01-31"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 1)  # Only header
        self.assertIn("date", lines[0])
        self.assertIn("start_time", lines[0])

    def test_export_with_signings(self):
        """Export returns CSV with signing data."""
        # Create a signing
        from django.utils import timezone
        start = timezone.make_aware(timezone.datetime(2026, 1, 15, 9, 0))
        end = timezone.make_aware(timezone.datetime(2026, 1, 15, 18, 0))

        Signing.objects.create(
            employee=self.user,
            start_time=start,
            end_time=end,
            location=self.location,
            description="Test signing",
        )

        url = reverse("signing-export")
        response = self.client.get(url, {"start_date": "2026-01-01", "end_date": "2026-01-31"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 2)  # Header + 1 signing
        self.assertIn("2026-01-15", lines[1])
        self.assertIn("540", lines[1])  # 9 hours = 540 minutes
        self.assertIn("Madrid HQ", lines[1])

    def test_export_filters_by_user(self):
        """Export only returns signings for authenticated user."""
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass"
        )

        from django.utils import timezone
        start = timezone.make_aware(timezone.datetime(2026, 1, 15, 9, 0))

        # Create signing for other user
        Signing.objects.create(employee=other_user, start_time=start)

        url = reverse("signing-export")
        response = self.client.get(url, {"start_date": "2026-01-01", "end_date": "2026-01-31"})

        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 1)  # Only header, no signings

    # ==================== IMPORT TESTS ====================

    def test_import_requires_authentication(self):
        """Import endpoint requires authentication."""
        self.client.force_authenticate(user=None)
        url = reverse("signing-import")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_import_requires_file(self):
        """Import requires a file."""
        url = reverse("signing-import")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No file provided", response.json()["error"])

    def test_import_requires_start_time_column(self):
        """Import requires start_time column in CSV."""
        url = reverse("signing-import")
        csv_content = "end_time,description\n2026-01-15 18:00,Test"
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "test.csv"

        response = self.client.post(url, {"file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_time", response.json()["error"])

    def test_import_valid_csv(self):
        """Import creates signings from valid CSV."""
        url = reverse("signing-import")
        csv_content = """start_time,end_time,location_id,description
2026-01-15 09:00,2026-01-15 18:00,,Work from home
2026-01-16 08:30,2026-01-16 17:30,,Another day"""

        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "signings.csv"

        response = self.client.post(url, {"file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["imported"], 2)
        self.assertEqual(response.json()["errors"], [])

        # Verify signings were created
        signings = Signing.objects.filter(employee=self.user)
        self.assertEqual(signings.count(), 2)

    def test_import_with_location(self):
        """Import creates signings with location and auto-creates WorkDay."""
        url = reverse("signing-import")
        csv_content = f"""start_time,end_time,location_id,description
2026-01-15 09:00,2026-01-15 18:00,{self.location.id},Office work"""

        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "signings.csv"

        response = self.client.post(url, {"file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["imported"], 1)

        # Verify signing has location
        signing = Signing.objects.get(employee=self.user)
        self.assertEqual(signing.location, self.location)

        # Verify WorkDay was created
        workday = WorkDay.objects.get(employee=self.user, date=date(2026, 1, 15))
        self.assertEqual(workday.location, self.location)
        self.assertEqual(signing.workday, workday)

    def test_import_invalid_date_format(self):
        """Import rejects rows with invalid date format."""
        url = reverse("signing-import")
        csv_content = """start_time,end_time,location_id,description
invalid-date,2026-01-15 18:00,,Test"""

        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "signings.csv"

        response = self.client.post(url, {"file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["imported"], 0)
        self.assertEqual(len(response.json()["errors"]), 1)
        self.assertEqual(response.json()["errors"][0]["row"], 2)
        self.assertIn("Invalid date format", response.json()["errors"][0]["error"])

    def test_import_invalid_location(self):
        """Import rejects rows with non-existent location."""
        url = reverse("signing-import")
        csv_content = """start_time,end_time,location_id,description
2026-01-15 09:00,2026-01-15 18:00,99999,Test"""

        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "signings.csv"

        response = self.client.post(url, {"file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["imported"], 0)
        self.assertIn("Location with id 99999 not found", response.json()["errors"][0]["error"])

    def test_import_atomic_transaction(self):
        """Import is atomic - if one row fails validation, nothing is imported."""
        url = reverse("signing-import")
        csv_content = """start_time,end_time,location_id,description
2026-01-15 09:00,2026-01-15 18:00,,Valid row
invalid-date,2026-01-16 18:00,,Invalid row"""

        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "signings.csv"

        response = self.client.post(url, {"file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["imported"], 0)

        # Verify no signings were created
        self.assertEqual(Signing.objects.filter(employee=self.user).count(), 0)

    def test_import_multiple_errors(self):
        """Import collects all validation errors."""
        url = reverse("signing-import")
        csv_content = """start_time,end_time,location_id,description
invalid-date,2026-01-15 18:00,,Row 2 error
2026-01-16 09:00,invalid-date,,Row 3 error
2026-01-17 09:00,2026-01-17 18:00,99999,Row 4 error"""

        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "signings.csv"

        response = self.client.post(url, {"file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.json()["errors"]), 3)

        # Check row numbers are correct
        rows = [e["row"] for e in response.json()["errors"]]
        self.assertEqual(rows, [2, 3, 4])

    def test_import_iso8601_format(self):
        """Import accepts ISO8601 datetime format."""
        url = reverse("signing-import")
        csv_content = """start_time,end_time,location_id,description
2026-01-15T09:00:00,2026-01-15T18:00:00,,ISO format"""

        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "signings.csv"

        response = self.client.post(url, {"file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["imported"], 1)

    def test_import_without_end_time(self):
        """Import allows rows without end_time (open signings)."""
        url = reverse("signing-import")
        csv_content = """start_time,end_time,location_id,description
2026-01-15 09:00,,,Started work"""

        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "signings.csv"

        response = self.client.post(url, {"file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["imported"], 1)

        signing = Signing.objects.get(employee=self.user)
        self.assertIsNone(signing.end_time)

    # ==================== ROUND-TRIP TEST ====================

    def test_export_import_roundtrip(self):
        """Data exported can be re-imported (excluding location names)."""
        from django.utils import timezone

        # Create initial signings
        for day in range(1, 4):
            start = timezone.make_aware(timezone.datetime(2026, 1, day, 9, 0))
            end = timezone.make_aware(timezone.datetime(2026, 1, day, 18, 0))
            Signing.objects.create(
                employee=self.user,
                start_time=start,
                end_time=end,
                description=f"Day {day}",
            )

        # Export
        export_url = reverse("signing-export")
        export_response = self.client.get(
            export_url, {"start_date": "2026-01-01", "end_date": "2026-01-31"}
        )
        self.assertEqual(export_response.status_code, status.HTTP_200_OK)

        # Delete original signings
        Signing.objects.filter(employee=self.user).delete()

        # Create import CSV (reformat export to import format)
        export_content = export_response.content.decode("utf-8")
        lines = export_content.strip().split("\n")

        # Build import CSV from export (start_time, end_time, location_id, description)
        import_lines = ["start_time,end_time,location_id,description"]
        for line in lines[1:]:  # Skip header
            parts = line.split(",")
            # date, start_time, end_time, duration_minutes, location, description
            start_time = parts[1]
            end_time = parts[2]
            description = parts[5] if len(parts) > 5 else ""
            import_lines.append(f"{start_time},{end_time},,{description}")

        import_csv = "\n".join(import_lines)

        # Import
        import_url = reverse("signing-import")
        csv_file = io.BytesIO(import_csv.encode("utf-8"))
        csv_file.name = "reimport.csv"

        import_response = self.client.post(import_url, {"file": csv_file}, format="multipart")
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        self.assertEqual(import_response.json()["imported"], 3)

        # Verify signings exist
        self.assertEqual(Signing.objects.filter(employee=self.user).count(), 3)
