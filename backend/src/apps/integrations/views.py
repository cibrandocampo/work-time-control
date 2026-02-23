from datetime import datetime

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import DayType
from apps.workdays.models import Signing, WorkDay

from .client import ExternalTimeManagerClient


@extend_schema(
    tags=["Integrations"],
    summary="Sync from external time manager",
    description="""Sync signings from an external time management system.

Requires an API token from the external system and a date range to sync.
The token is used only for this request and is not stored.
""",
)
class SyncView(APIView):
    """Sync signings from external time manager."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("token")
        api_key = request.data.get("api_key")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not token or not api_key:
            return Response(
                {"error": "API token and api_key are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not start_date or not end_date:
            return Response(
                {"error": "start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get external user ID
        external_user_id = request.user.external_user_id

        # Get company external ID from user's first location's company
        external_company_id = None
        first_location = request.user.locations.first()
        if first_location and first_location.company.external_id:
            external_company_id = first_location.company.external_id

        if not external_user_id:
            return Response(
                {"error": "User external ID not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not external_company_id:
            return Response(
                {"error": "Company external ID not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Initialize client
        client = ExternalTimeManagerClient(token, api_key, external_company_id)

        if not client.is_configured:
            return Response(
                {"error": "External time manager not configured"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        # Get or create working day type
        working_day_type, _ = DayType.objects.get_or_create(
            name="Working",
            defaults={"requires_signing": True},
        )

        # Fetch data from external system
        try:
            days_data = client.fetch_range(external_user_id, start_date, end_date)
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch data: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not days_data:
            return Response(
                {"error": "No data received from external system"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Import signings
        imported_count = 0
        errors = []

        with transaction.atomic():
            for day_data in days_data:
                date_str = day_data.get("date")
                signings = client.parse_signings(day_data)

                for signing_data in signings:
                    try:
                        # Parse datetime
                        start_time = datetime.fromisoformat(
                            signing_data["start_time"].replace(" ", "T")
                        )
                        end_time = None
                        if signing_data.get("end_time"):
                            end_time = datetime.fromisoformat(
                                signing_data["end_time"].replace(" ", "T")
                            )

                        # Get or create WorkDay
                        work_day, _ = WorkDay.objects.get_or_create(
                            date=start_time.date(),
                            employee=request.user,
                            location=first_location,
                            defaults={"day_type": working_day_type},
                        )

                        # Check for duplicate (same start_time)
                        existing = Signing.objects.filter(
                            employee=request.user,
                            start_time=start_time,
                        ).exists()

                        if existing:
                            continue

                        # Create signing
                        Signing.objects.create(
                            employee=request.user,
                            workday=work_day,
                            location=first_location,
                            start_time=start_time,
                            end_time=end_time,
                            description=signing_data.get("description", ""),
                        )
                        imported_count += 1

                    except Exception as e:
                        errors.append({"date": date_str, "error": str(e)})

        return Response(
            {
                "imported": imported_count,
                "errors": errors,
            },
            status=status.HTTP_200_OK,
        )
