"""Client for external time manager API."""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class ExternalTimeManagerClient:
    """Client to fetch signings from external time manager."""

    def __init__(self, token: str, api_key: str = None, company_id: str = None):
        self.base_url = os.getenv("EXTERNAL_TIME_MANAGER_URL")
        self.company_id = company_id or os.getenv("EXTERNAL_TIME_MANAGER_COMPANY_ID")
        self.api_key = api_key
        self.token = token

    @property
    def is_configured(self) -> bool:
        """Check if the external time manager is configured."""
        return bool(self.base_url)

    def get_headers(self) -> dict:
        """Get request headers with authorization."""
        headers = {
            "authorization": self.token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["api-key"] = self.api_key
        return headers

    def fetch_day(self, user_id: str, date: str) -> Optional[dict]:
        """
        Fetch signings for a specific day.

        Args:
            user_id: External user ID
            date: Date in YYYY-MM-DD format

        Returns:
            API response data or None on error
        """
        url = f"{self.base_url}/api/v1/admin/company/{self.company_id}/users/{user_id}/day/{date}"
        logger.info(f"Fetching: {url}")

        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text[:500]}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def fetch_range(self, user_id: str, start_date: str, end_date: str) -> list[dict]:
        """
        Fetch signings for a date range.

        Args:
            user_id: External user ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of daily signing data
        """
        results = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            day_data = self.fetch_day(user_id, date_str)
            if day_data:
                day_data["date"] = date_str
                results.append(day_data)
            current += timedelta(days=1)

        return results

    def parse_signings(self, day_data: dict) -> list[dict]:
        """
        Parse external API response into signing records.

        Expected format from external API:
        {
            "checks": [
                {"checkin": "2026-02-08 09:00:00", "checkout": "2026-02-08 14:00:00", "op_in": "Oficina"},
                {"checkin": "2026-02-08 15:00:00", "checkout": "2026-02-08 18:00:00", "op_in": "Teletrabajo"}
            ],
            "total_minutes": 480,
            "planned_minutes": 510
        }

        Returns:
            List of signing dicts ready to create
        """
        signings = []
        checks = day_data.get("checks", [])

        for check in checks:
            checkin = check.get("checkin")
            checkout = check.get("checkout")
            location_type = check.get("op_in") or ""
            notes = check.get("notes") or ""

            if checkin:
                signing = {
                    "start_time": checkin,
                    "end_time": checkout,
                    "description": notes,
                    "work_location": "remote" if "teletrabajo" in location_type.lower() else "office",
                }
                signings.append(signing)

        return signings
