"""Tests for integrations app - client and views."""
import os
from datetime import datetime
from unittest.mock import patch, MagicMock, call

import pytest
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.accounts.models import User
from apps.companies.models import Company, Location
from apps.core.models import DayType
from apps.workdays.models import Signing, WorkDay
from apps.integrations.client import ExternalTimeManagerClient


# ==================== CLIENT UNIT TESTS ====================


class ExternalTimeManagerClientConfigurationTest(TestCase):
    """Tests for client configuration."""

    def test_is_configured_returns_false_when_not_configured(self):
        """Client reports not configured when env vars missing."""
        with patch.dict(os.environ, {}, clear=True):
            client = ExternalTimeManagerClient("test-token")
            self.assertFalse(client.is_configured)

    def test_is_configured_returns_true_when_url_configured(self):
        """Client reports configured when URL is present."""
        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
        }):
            client = ExternalTimeManagerClient("test-token")
            self.assertTrue(client.is_configured)

    def test_is_configured_returns_true_when_fully_configured(self):
        """Client reports configured when all env vars present."""
        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
            "EXTERNAL_TIME_MANAGER_COMPANY_ID": "1",
        }):
            client = ExternalTimeManagerClient("test-token")
            self.assertTrue(client.is_configured)

    def test_constructor_uses_env_company_id(self):
        """Constructor uses EXTERNAL_TIME_MANAGER_COMPANY_ID from env."""
        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
            "EXTERNAL_TIME_MANAGER_COMPANY_ID": "123",
        }):
            client = ExternalTimeManagerClient("token")
            self.assertEqual(client.company_id, "123")

    def test_constructor_overrides_env_company_id(self):
        """Constructor parameter overrides env company_id."""
        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
            "EXTERNAL_TIME_MANAGER_COMPANY_ID": "123",
        }):
            client = ExternalTimeManagerClient("token", company_id="456")
            self.assertEqual(client.company_id, "456")

    def test_constructor_stores_api_key(self):
        """Constructor stores api_key parameter."""
        client = ExternalTimeManagerClient("token", api_key="my-api-key")
        self.assertEqual(client.api_key, "my-api-key")

    def test_constructor_stores_token(self):
        """Constructor stores token parameter."""
        client = ExternalTimeManagerClient("my-secret-token")
        self.assertEqual(client.token, "my-secret-token")


class ExternalTimeManagerClientHeadersTest(TestCase):
    """Tests for client headers generation."""

    def test_get_headers_includes_authorization(self):
        """Headers include authorization token."""
        client = ExternalTimeManagerClient("my-secret-token")
        headers = client.get_headers()

        self.assertEqual(headers["authorization"], "my-secret-token")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Accept"], "application/json")

    def test_get_headers_without_api_key(self):
        """Headers do not include api-key when not provided."""
        client = ExternalTimeManagerClient("token")
        headers = client.get_headers()

        self.assertNotIn("api-key", headers)

    def test_get_headers_with_api_key(self):
        """Headers include api-key when provided."""
        client = ExternalTimeManagerClient("token", api_key="my-api-key")
        headers = client.get_headers()

        self.assertEqual(headers["api-key"], "my-api-key")


class ExternalTimeManagerClientParseSigningsTest(TestCase):
    """Tests for parse_signings method."""

    def test_parse_signings_empty_checks(self):
        """Parse signings handles empty checks list."""
        client = ExternalTimeManagerClient("token")
        result = client.parse_signings({"checks": []})
        self.assertEqual(result, [])

    def test_parse_signings_no_checks_key(self):
        """Parse signings handles missing checks key."""
        client = ExternalTimeManagerClient("token")
        result = client.parse_signings({})
        self.assertEqual(result, [])

    def test_parse_signings_with_complete_data(self):
        """Parse signings extracts all fields correctly."""
        client = ExternalTimeManagerClient("token")
        day_data = {
            "checks": [
                {
                    "checkin": "2026-02-08 09:00:00",
                    "checkout": "2026-02-08 14:00:00",
                    "op_in": "Oficina",
                    "notes": "Morning shift",
                },
            ]
        }

        result = client.parse_signings(day_data)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start_time"], "2026-02-08 09:00:00")
        self.assertEqual(result[0]["end_time"], "2026-02-08 14:00:00")
        self.assertEqual(result[0]["work_location"], "office")
        self.assertEqual(result[0]["description"], "Morning shift")

    def test_parse_signings_multiple_checks(self):
        """Parse signings handles multiple checks."""
        client = ExternalTimeManagerClient("token")
        day_data = {
            "checks": [
                {
                    "checkin": "2026-02-08 09:00:00",
                    "checkout": "2026-02-08 14:00:00",
                    "op_in": "Oficina",
                },
                {
                    "checkin": "2026-02-08 15:00:00",
                    "checkout": "2026-02-08 18:00:00",
                    "op_in": "Teletrabajo",
                },
            ]
        }

        result = client.parse_signings(day_data)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["work_location"], "office")
        self.assertEqual(result[1]["work_location"], "remote")

    def test_parse_signings_teletrabajo_location(self):
        """Parse signings maps 'Teletrabajo' to remote."""
        client = ExternalTimeManagerClient("token")
        day_data = {
            "checks": [
                {"checkin": "2026-02-08 09:00:00", "op_in": "Teletrabajo"},
            ]
        }

        result = client.parse_signings(day_data)
        self.assertEqual(result[0]["work_location"], "remote")

    def test_parse_signings_teletrabajo_case_insensitive(self):
        """Parse signings handles teletrabajo in different cases."""
        client = ExternalTimeManagerClient("token")

        for location in ["TELETRABAJO", "teletrabajo", "TeleTrabajo"]:
            day_data = {
                "checks": [{"checkin": "2026-02-08 09:00:00", "op_in": location}]
            }
            result = client.parse_signings(day_data)
            self.assertEqual(result[0]["work_location"], "remote")

    def test_parse_signings_office_location(self):
        """Parse signings maps 'Oficina' and others to office."""
        client = ExternalTimeManagerClient("token")

        for location in ["Oficina", "Cliente", "Pausa cafe", ""]:
            day_data = {
                "checks": [{"checkin": "2026-02-08 09:00:00", "op_in": location}]
            }
            result = client.parse_signings(day_data)
            self.assertEqual(result[0]["work_location"], "office")

    def test_parse_signings_missing_checkout(self):
        """Parse signings handles missing checkout (open signing)."""
        client = ExternalTimeManagerClient("token")
        day_data = {
            "checks": [
                {"checkin": "2026-02-08 09:00:00", "op_in": "Oficina"},
            ]
        }

        result = client.parse_signings(day_data)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["end_time"])

    def test_parse_signings_missing_notes(self):
        """Parse signings handles missing notes."""
        client = ExternalTimeManagerClient("token")
        day_data = {
            "checks": [
                {"checkin": "2026-02-08 09:00:00", "checkout": "2026-02-08 18:00:00"},
            ]
        }

        result = client.parse_signings(day_data)
        self.assertEqual(result[0]["description"], "")

    def test_parse_signings_missing_op_in(self):
        """Parse signings handles missing op_in (location type)."""
        client = ExternalTimeManagerClient("token")
        day_data = {
            "checks": [
                {"checkin": "2026-02-08 09:00:00"},
            ]
        }

        result = client.parse_signings(day_data)
        self.assertEqual(result[0]["work_location"], "office")

    def test_parse_signings_skips_entries_without_checkin(self):
        """Parse signings skips entries without checkin."""
        client = ExternalTimeManagerClient("token")
        day_data = {
            "checks": [
                {"checkout": "2026-02-08 18:00:00"},  # No checkin
                {"checkin": "2026-02-08 09:00:00"},  # Valid
            ]
        }

        result = client.parse_signings(day_data)
        self.assertEqual(len(result), 1)


class ExternalTimeManagerClientFetchDayTest(TestCase):
    """Tests for fetch_day method."""

    @patch("apps.integrations.client.requests.get")
    def test_fetch_day_success(self, mock_get):
        """Fetch day returns data on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"checks": [], "total_minutes": 480}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
            "EXTERNAL_TIME_MANAGER_COMPANY_ID": "1",
        }):
            client = ExternalTimeManagerClient("token")
            result = client.fetch_day("123", "2026-02-08")

        self.assertEqual(result, {"checks": [], "total_minutes": 480})

    @patch("apps.integrations.client.requests.get")
    def test_fetch_day_builds_correct_url(self, mock_get):
        """Fetch day constructs the correct API URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://api.example.com",
        }):
            client = ExternalTimeManagerClient("token", company_id="42")
            client.fetch_day("123", "2026-02-08")

        expected_url = "https://api.example.com/api/v1/admin/company/42/users/123/day/2026-02-08"
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args[0][0], expected_url)

    @patch("apps.integrations.client.requests.get")
    def test_fetch_day_sends_headers(self, mock_get):
        """Fetch day sends proper headers."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
        }):
            client = ExternalTimeManagerClient("my-token", api_key="my-key", company_id="1")
            client.fetch_day("123", "2026-02-08")

        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs["headers"]
        self.assertEqual(headers["authorization"], "my-token")
        self.assertEqual(headers["api-key"], "my-key")

    @patch("apps.integrations.client.requests.get")
    def test_fetch_day_uses_timeout(self, mock_get):
        """Fetch day uses timeout parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
        }):
            client = ExternalTimeManagerClient("token", company_id="1")
            client.fetch_day("123", "2026-02-08")

        call_kwargs = mock_get.call_args[1]
        self.assertEqual(call_kwargs["timeout"], 30)

    @patch("apps.integrations.client.requests.get")
    def test_fetch_day_returns_none_on_request_exception(self, mock_get):
        """Fetch day returns None on request exception."""
        import requests
        mock_get.side_effect = requests.RequestException("Connection error")

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
        }):
            client = ExternalTimeManagerClient("token", company_id="1")
            result = client.fetch_day("123", "2026-02-08")

        self.assertIsNone(result)

    @patch("apps.integrations.client.requests.get")
    def test_fetch_day_returns_none_on_http_error(self, mock_get):
        """Fetch day returns None on HTTP error response."""
        import requests
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
        }):
            client = ExternalTimeManagerClient("token", company_id="1")
            result = client.fetch_day("123", "2026-02-08")

        self.assertIsNone(result)


class ExternalTimeManagerClientFetchRangeTest(TestCase):
    """Tests for fetch_range method."""

    @patch.object(ExternalTimeManagerClient, "fetch_day")
    def test_fetch_range_single_day(self, mock_fetch_day):
        """Fetch range with same start and end date fetches one day."""
        mock_fetch_day.return_value = {"checks": []}

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
        }):
            client = ExternalTimeManagerClient("token", company_id="1")
            result = client.fetch_range("123", "2026-02-08", "2026-02-08")

        mock_fetch_day.assert_called_once_with("123", "2026-02-08")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["date"], "2026-02-08")

    @patch.object(ExternalTimeManagerClient, "fetch_day")
    def test_fetch_range_multiple_days(self, mock_fetch_day):
        """Fetch range iterates over all days in range."""
        mock_fetch_day.return_value = {"checks": []}

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
        }):
            client = ExternalTimeManagerClient("token", company_id="1")
            result = client.fetch_range("123", "2026-02-01", "2026-02-03")

        self.assertEqual(mock_fetch_day.call_count, 3)
        mock_fetch_day.assert_any_call("123", "2026-02-01")
        mock_fetch_day.assert_any_call("123", "2026-02-02")
        mock_fetch_day.assert_any_call("123", "2026-02-03")

        self.assertEqual(len(result), 3)

    @patch.object(ExternalTimeManagerClient, "fetch_day")
    def test_fetch_range_adds_date_to_results(self, mock_fetch_day):
        """Fetch range adds date field to each result."""
        # Each call returns a new dict to avoid mutation issues
        mock_fetch_day.side_effect = [
            {"checks": [], "total_minutes": 480},
            {"checks": [], "total_minutes": 480},
        ]

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
        }):
            client = ExternalTimeManagerClient("token", company_id="1")
            result = client.fetch_range("123", "2026-02-01", "2026-02-02")

        self.assertEqual(result[0]["date"], "2026-02-01")
        self.assertEqual(result[1]["date"], "2026-02-02")
        # Original data should still be present
        self.assertEqual(result[0]["total_minutes"], 480)

    @patch.object(ExternalTimeManagerClient, "fetch_day")
    def test_fetch_range_skips_failed_days(self, mock_fetch_day):
        """Fetch range skips days that return None."""
        mock_fetch_day.side_effect = [
            {"checks": []},  # Day 1 OK
            None,            # Day 2 fails
            {"checks": []},  # Day 3 OK
        ]

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
        }):
            client = ExternalTimeManagerClient("token", company_id="1")
            result = client.fetch_range("123", "2026-02-01", "2026-02-03")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["date"], "2026-02-01")
        self.assertEqual(result[1]["date"], "2026-02-03")

    @patch.object(ExternalTimeManagerClient, "fetch_day")
    def test_fetch_range_all_days_fail(self, mock_fetch_day):
        """Fetch range returns empty list if all days fail."""
        mock_fetch_day.return_value = None

        with patch.dict(os.environ, {
            "EXTERNAL_TIME_MANAGER_URL": "https://example.com",
        }):
            client = ExternalTimeManagerClient("token", company_id="1")
            result = client.fetch_range("123", "2026-02-01", "2026-02-03")

        self.assertEqual(result, [])


# ==================== SYNC VIEW API TESTS ====================


class SyncViewAuthenticationTest(APITestCase):
    """Tests for SyncView authentication requirements."""

    def test_sync_requires_authentication(self):
        """Sync endpoint requires authentication."""
        response = self.client.post("/api/integrations/sync/", {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SyncViewValidationTest(APITestCase):
    """Tests for SyncView request validation."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", external_id="ext-123")
        self.location = Location.objects.create(
            company=self.company,
            name="Madrid HQ",
            latitude=40.4168,
            longitude=-3.7038,
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            external_user_id="2431",
        )
        self.user.locations.add(self.location)
        self.client.force_authenticate(user=self.user)

    def test_sync_requires_token(self):
        """Sync endpoint requires API token."""
        response = self.client.post("/api/integrations/sync/", {
            "api_key": "api-key",
            "start_date": "2026-02-01",
            "end_date": "2026-02-08",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("token", response.data["error"].lower())

    def test_sync_requires_api_key(self):
        """Sync endpoint requires API key."""
        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "start_date": "2026-02-01",
            "end_date": "2026-02-08",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("api_key", response.data["error"].lower())

    def test_sync_requires_start_date(self):
        """Sync endpoint requires start_date."""
        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "end_date": "2026-02-08",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data["error"].lower())

    def test_sync_requires_end_date(self):
        """Sync endpoint requires end_date."""
        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-01",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data["error"].lower())


class SyncViewUserConfigurationTest(APITestCase):
    """Tests for SyncView user configuration validation."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", external_id="ext-123")
        self.location = Location.objects.create(
            company=self.company,
            name="Madrid HQ",
            latitude=40.4168,
            longitude=-3.7038,
        )

    def test_sync_requires_user_external_id(self):
        """Sync returns error if user has no external_user_id."""
        user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            external_user_id=None,  # Not configured
        )
        user.locations.add(self.location)
        self.client.force_authenticate(user=user)

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-01",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("external", response.data["error"].lower())

    def test_sync_requires_company_external_id(self):
        """Sync returns error if company has no external_id."""
        company_no_ext = Company.objects.create(name="No External ID")
        location_no_ext = Location.objects.create(
            company=company_no_ext,
            name="Remote",
            latitude=0,
            longitude=0,
        )
        user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            external_user_id="2431",
        )
        user.locations.add(location_no_ext)
        self.client.force_authenticate(user=user)

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-01",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company", response.data["error"].lower())

    def test_sync_requires_user_location(self):
        """Sync returns error if user has no locations."""
        user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            external_user_id="2431",
        )
        # User has no locations
        self.client.force_authenticate(user=user)

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-01",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company", response.data["error"].lower())


class SyncViewClientConfigurationTest(APITestCase):
    """Tests for SyncView when client is not configured."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", external_id="ext-123")
        self.location = Location.objects.create(
            company=self.company,
            name="Madrid HQ",
            latitude=40.4168,
            longitude=-3.7038,
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            external_user_id="2431",
        )
        self.user.locations.add(self.location)
        self.client.force_authenticate(user=self.user)

    def test_sync_not_configured_returns_501(self):
        """Sync returns 501 when external system not configured."""
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post("/api/integrations/sync/", {
                "token": "test-token",
                "api_key": "api-key",
                "start_date": "2026-02-01",
                "end_date": "2026-02-08",
            })
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
        self.assertIn("not configured", response.data["error"].lower())


class SyncViewFetchErrorsTest(APITestCase):
    """Tests for SyncView error handling when fetching data."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", external_id="ext-123")
        self.location = Location.objects.create(
            company=self.company,
            name="Madrid HQ",
            latitude=40.4168,
            longitude=-3.7038,
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            external_user_id="2431",
        )
        self.user.locations.add(self.location)
        self.client.force_authenticate(user=self.user)

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_fetch_exception_returns_502(self, MockClient):
        """Sync returns 502 when fetch raises exception."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.side_effect = Exception("Network error")
        MockClient.return_value = mock_client

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("failed to fetch", response.data["error"].lower())

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_empty_data_returns_502(self, MockClient):
        """Sync returns 502 when no data received."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = []
        MockClient.return_value = mock_client

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("no data", response.data["error"].lower())


class SyncViewSuccessTest(APITestCase):
    """Tests for successful SyncView operations."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", external_id="ext-123")
        self.location = Location.objects.create(
            company=self.company,
            name="Madrid HQ",
            latitude=40.4168,
            longitude=-3.7038,
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            external_user_id="2431",
        )
        self.user.locations.add(self.location)
        self.client.force_authenticate(user=self.user)

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_success_single_signing(self, MockClient):
        """Sync imports single signing successfully."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [
            {
                "date": "2026-02-08",
                "checks": [
                    {
                        "checkin": "2026-02-08 09:00:00",
                        "checkout": "2026-02-08 18:00:00",
                        "op_in": "Oficina",
                    }
                ],
            }
        ]
        mock_client.parse_signings.return_value = [
            {
                "start_time": "2026-02-08 09:00:00",
                "end_time": "2026-02-08 18:00:00",
                "description": "",
                "work_location": "office",
            }
        ]
        MockClient.return_value = mock_client

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["imported"], 1)
        self.assertEqual(response.data["errors"], [])

        # Verify signing was created
        signing = Signing.objects.get(employee=self.user)
        self.assertEqual(signing.start_time.strftime("%Y-%m-%d %H:%M"), "2026-02-08 09:00")
        self.assertEqual(signing.end_time.strftime("%Y-%m-%d %H:%M"), "2026-02-08 18:00")

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_success_multiple_signings(self, MockClient):
        """Sync imports multiple signings successfully."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [
            {"date": "2026-02-08", "checks": []},
            {"date": "2026-02-09", "checks": []},
        ]
        mock_client.parse_signings.side_effect = [
            [
                {
                    "start_time": "2026-02-08 09:00:00",
                    "end_time": "2026-02-08 18:00:00",
                    "description": "",
                    "work_location": "office",
                }
            ],
            [
                {
                    "start_time": "2026-02-09 09:00:00",
                    "end_time": "2026-02-09 18:00:00",
                    "description": "",
                    "work_location": "remote",
                }
            ],
        ]
        MockClient.return_value = mock_client

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-09",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["imported"], 2)
        self.assertEqual(Signing.objects.filter(employee=self.user).count(), 2)

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_creates_workday(self, MockClient):
        """Sync creates WorkDay for each signing."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [{"date": "2026-02-08", "checks": []}]
        mock_client.parse_signings.return_value = [
            {
                "start_time": "2026-02-08 09:00:00",
                "end_time": "2026-02-08 18:00:00",
                "description": "",
                "work_location": "office",
            }
        ]
        MockClient.return_value = mock_client

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify WorkDay was created
        workday = WorkDay.objects.get(employee=self.user, date="2026-02-08")
        self.assertEqual(workday.location, self.location)
        self.assertEqual(workday.day_type.name, "Working")

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_links_signing_to_workday(self, MockClient):
        """Sync links signing to the created WorkDay."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [{"date": "2026-02-08", "checks": []}]
        mock_client.parse_signings.return_value = [
            {
                "start_time": "2026-02-08 09:00:00",
                "end_time": "2026-02-08 18:00:00",
                "description": "",
                "work_location": "office",
            }
        ]
        MockClient.return_value = mock_client

        self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        signing = Signing.objects.get(employee=self.user)
        workday = WorkDay.objects.get(employee=self.user, date="2026-02-08")
        self.assertEqual(signing.workday, workday)

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_open_signing_no_end_time(self, MockClient):
        """Sync handles open signings without end time."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [{"date": "2026-02-08", "checks": []}]
        mock_client.parse_signings.return_value = [
            {
                "start_time": "2026-02-08 09:00:00",
                "end_time": None,  # Open signing
                "description": "Still working",
                "work_location": "office",
            }
        ]
        MockClient.return_value = mock_client

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["imported"], 1)

        signing = Signing.objects.get(employee=self.user)
        self.assertIsNone(signing.end_time)

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_stores_description(self, MockClient):
        """Sync stores description from parsed signings."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [{"date": "2026-02-08", "checks": []}]
        mock_client.parse_signings.return_value = [
            {
                "start_time": "2026-02-08 09:00:00",
                "end_time": "2026-02-08 18:00:00",
                "description": "Working on project X",
                "work_location": "office",
            }
        ]
        MockClient.return_value = mock_client

        self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        signing = Signing.objects.get(employee=self.user)
        self.assertEqual(signing.description, "Working on project X")


class SyncViewDuplicateHandlingTest(APITestCase):
    """Tests for SyncView duplicate signing handling."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", external_id="ext-123")
        self.location = Location.objects.create(
            company=self.company,
            name="Madrid HQ",
            latitude=40.4168,
            longitude=-3.7038,
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            external_user_id="2431",
        )
        self.user.locations.add(self.location)
        self.client.force_authenticate(user=self.user)

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_skips_duplicate_signings(self, MockClient):
        """Sync skips signings with same start_time that already exist."""
        # Create existing signing
        start_time = timezone.make_aware(datetime(2026, 2, 8, 9, 0))
        Signing.objects.create(
            employee=self.user,
            start_time=start_time,
            location=self.location,
        )

        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [{"date": "2026-02-08", "checks": []}]
        mock_client.parse_signings.return_value = [
            {
                "start_time": "2026-02-08 09:00:00",  # Same as existing
                "end_time": "2026-02-08 18:00:00",
                "description": "",
                "work_location": "office",
            }
        ]
        MockClient.return_value = mock_client

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["imported"], 0)  # Skipped

        # Still only one signing
        self.assertEqual(Signing.objects.filter(employee=self.user).count(), 1)

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_imports_non_duplicate_signings(self, MockClient):
        """Sync imports signings that don't already exist."""
        # Create existing signing for different time
        existing_time = timezone.make_aware(datetime(2026, 2, 8, 7, 0))
        Signing.objects.create(
            employee=self.user,
            start_time=existing_time,
            location=self.location,
        )

        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [{"date": "2026-02-08", "checks": []}]
        mock_client.parse_signings.return_value = [
            {
                "start_time": "2026-02-08 09:00:00",  # Different from existing
                "end_time": "2026-02-08 18:00:00",
                "description": "",
                "work_location": "office",
            }
        ]
        MockClient.return_value = mock_client

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["imported"], 1)

        # Now two signings
        self.assertEqual(Signing.objects.filter(employee=self.user).count(), 2)

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_mixed_duplicates_and_new(self, MockClient):
        """Sync correctly handles mix of duplicate and new signings."""
        # Create existing signing
        existing_time = timezone.make_aware(datetime(2026, 2, 8, 9, 0))
        Signing.objects.create(
            employee=self.user,
            start_time=existing_time,
            location=self.location,
        )

        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [{"date": "2026-02-08", "checks": []}]
        mock_client.parse_signings.return_value = [
            {
                "start_time": "2026-02-08 09:00:00",  # Duplicate
                "end_time": "2026-02-08 14:00:00",
                "description": "",
                "work_location": "office",
            },
            {
                "start_time": "2026-02-08 15:00:00",  # New
                "end_time": "2026-02-08 18:00:00",
                "description": "",
                "work_location": "office",
            },
        ]
        MockClient.return_value = mock_client

        response = self.client.post("/api/integrations/sync/", {
            "token": "test-token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["imported"], 1)  # Only the new one

        self.assertEqual(Signing.objects.filter(employee=self.user).count(), 2)


class SyncViewClientInitializationTest(APITestCase):
    """Tests for how SyncView initializes the client."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", external_id="ext-123")
        self.location = Location.objects.create(
            company=self.company,
            name="Madrid HQ",
            latitude=40.4168,
            longitude=-3.7038,
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            external_user_id="2431",
        )
        self.user.locations.add(self.location)
        self.client.force_authenticate(user=self.user)

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_passes_token_to_client(self, MockClient):
        """Sync passes token to ExternalTimeManagerClient."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [{"date": "2026-02-08", "checks": []}]
        mock_client.parse_signings.return_value = []
        MockClient.return_value = mock_client

        self.client.post("/api/integrations/sync/", {
            "token": "my-secret-token",
            "api_key": "my-api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        MockClient.assert_called_once_with("my-secret-token", "my-api-key", "ext-123")

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_passes_company_external_id_to_client(self, MockClient):
        """Sync passes company external_id to ExternalTimeManagerClient."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [{"date": "2026-02-08", "checks": []}]
        mock_client.parse_signings.return_value = []
        MockClient.return_value = mock_client

        self.client.post("/api/integrations/sync/", {
            "token": "token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-08",
        })

        # Check that company external_id was passed
        call_args = MockClient.call_args[0]
        self.assertEqual(call_args[2], "ext-123")

    @patch("apps.integrations.views.ExternalTimeManagerClient")
    def test_sync_calls_fetch_range_with_user_external_id(self, MockClient):
        """Sync uses user's external_user_id for fetch_range."""
        mock_client = MagicMock()
        mock_client.is_configured = True
        mock_client.fetch_range.return_value = [{"date": "2026-02-08", "checks": []}]
        mock_client.parse_signings.return_value = []
        MockClient.return_value = mock_client

        self.client.post("/api/integrations/sync/", {
            "token": "token",
            "api_key": "api-key",
            "start_date": "2026-02-08",
            "end_date": "2026-02-10",
        })

        mock_client.fetch_range.assert_called_once_with("2431", "2026-02-08", "2026-02-10")


# ==================== PYTEST-STYLE TESTS ====================


@pytest.mark.django_db
class TestClientWithPytest:
    """Additional client tests using pytest style for consistency with other apps."""

    def test_client_is_not_configured_by_default(self):
        """Client is not configured without env vars."""
        with patch.dict(os.environ, {}, clear=True):
            client = ExternalTimeManagerClient("token")
            assert not client.is_configured

    def test_parse_signings_returns_list(self):
        """parse_signings always returns a list."""
        client = ExternalTimeManagerClient("token")
        result = client.parse_signings({})
        assert isinstance(result, list)

    def test_parse_signings_preserves_order(self):
        """parse_signings preserves order of checks."""
        client = ExternalTimeManagerClient("token")
        day_data = {
            "checks": [
                {"checkin": "2026-02-08 09:00:00"},
                {"checkin": "2026-02-08 15:00:00"},
                {"checkin": "2026-02-08 12:00:00"},
            ]
        }
        result = client.parse_signings(day_data)

        assert len(result) == 3
        assert result[0]["start_time"] == "2026-02-08 09:00:00"
        assert result[1]["start_time"] == "2026-02-08 15:00:00"
        assert result[2]["start_time"] == "2026-02-08 12:00:00"


@pytest.mark.django_db
class TestSyncViewWithPytest:
    """Additional sync view tests using pytest style."""

    def test_sync_url_exists(self, api_client, user):
        """Sync endpoint exists at expected URL."""
        api_client.force_authenticate(user=user)
        response = api_client.post("/api/integrations/sync/", {})
        # Should get 400 for missing params, not 404
        assert response.status_code != 404

    def test_sync_only_accepts_post(self, api_client, user):
        """Sync endpoint only accepts POST."""
        api_client.force_authenticate(user=user)

        get_response = api_client.get("/api/integrations/sync/")
        assert get_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        put_response = api_client.put("/api/integrations/sync/", {})
        assert put_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        delete_response = api_client.delete("/api/integrations/sync/")
        assert delete_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
