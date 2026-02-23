import csv
import io
from collections import defaultdict
from datetime import date, datetime, timedelta

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import Location
from apps.core.models import DayType

from .models import Signing, WorkDay
from .serializers import (
    DaySummarySerializer,
    SigningCreateSerializer,
    SigningSerializer,
    SigningUpdateSerializer,
    WorkDaySerializer,
)


@extend_schema_view(
    list=extend_schema(
        tags=["Work Days"],
        summary="List work days",
        description="Get all work days for the authenticated user.",
    ),
    create=extend_schema(
        tags=["Work Days"],
        summary="Create work day",
        description="Create a new work day record for a specific date and location.",
    ),
    retrieve=extend_schema(
        tags=["Work Days"],
        summary="Get work day",
        description="Get details of a specific work day.",
    ),
    update=extend_schema(
        tags=["Work Days"],
        summary="Update work day",
        description="Fully update an existing work day.",
    ),
    partial_update=extend_schema(
        tags=["Work Days"],
        summary="Partial update work day",
        description="Update one or more fields of a work day.",
    ),
    destroy=extend_schema(
        tags=["Work Days"],
        summary="Delete work day",
        description="Delete a work day. Associated signings will be unlinked.",
    ),
)
class WorkDayViewSet(viewsets.ModelViewSet):
    """
    Work day management.

    Work days define the day type (working, vacation, holiday, etc.)
    and expected hours for each date at a specific location.
    """
    serializer_class = WorkDaySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkDay.objects.filter(
            employee=self.request.user
        ).select_related("day_type", "location")

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user)


@extend_schema_view(
    list=extend_schema(
        tags=["Signings"],
        summary="List signings",
        description="Get all signings for the authenticated user, ordered by date.",
    ),
    create=extend_schema(
        tags=["Signings"],
        summary="Create signing (check-in)",
        description="Record a new check-in. A work day is automatically created if none exists for that day and location.",
    ),
    retrieve=extend_schema(
        tags=["Signings"],
        summary="Get signing",
        description="Get details of a specific signing.",
    ),
    update=extend_schema(
        tags=["Signings"],
        summary="Update signing",
        description="Fully update an existing signing.",
    ),
    partial_update=extend_schema(
        tags=["Signings"],
        summary="Partial update signing",
        description="Update one or more fields of a signing.",
    ),
    destroy=extend_schema(
        tags=["Signings"],
        summary="Delete signing",
        description="Delete a signing from the records.",
    ),
)
class SigningViewSet(viewsets.ModelViewSet):
    """
    Signing management.

    Allows recording check-ins and check-outs at specific locations.
    """
    serializer_class = SigningSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Signing.objects.filter(
            employee=self.request.user
        ).select_related("location", "workday")

        # Filter by date range if provided
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return SigningCreateSerializer
        if self.action in ["update", "partial_update"]:
            return SigningUpdateSerializer
        return SigningSerializer

    def perform_create(self, serializer):
        """Create signing and auto-create WorkDay if needed."""
        signing = serializer.save(employee=self.request.user)

        # Auto-create WorkDay for this day and location if it doesn't exist
        if signing.location:
            signing_date = signing.start_time.date()
            workday, created = WorkDay.objects.get_or_create(
                date=signing_date,
                employee=self.request.user,
                location=signing.location,
                defaults={
                    "day_type": DayType.objects.get_or_create(
                        name="Working", defaults={"requires_signing": True}
                    )[0]
                },
            )

            # Link signing to workday
            signing.workday = workday
            signing.save(update_fields=["workday"])

    @extend_schema(
        tags=["Signings"],
        summary="Get active signing",
        description="Returns the ongoing signing (without end time) for the authenticated user. Returns null if none is active.",
    )
    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get active signing (started but not ended)."""
        active = self.get_queryset().filter(end_time__isnull=True).first()
        if active:
            return Response(SigningSerializer(active).data)
        return Response({"active": None})

    @extend_schema(
        tags=["Signings"],
        summary="Finish signing (check-out)",
        description="Record the end time for an active signing. If end_time is not provided, current time is used.",
    )
    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        """End an active signing."""
        signing = self.get_object()
        if signing.end_time:
            return Response(
                {"error": "Signing already ended"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SigningUpdateSerializer(signing, data=request.data, partial=True)
        if serializer.is_valid():
            if not serializer.validated_data.get("end_time"):
                serializer.validated_data["end_time"] = timezone.now()
            serializer.save()
            return Response(SigningSerializer(signing).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["Summaries"],
    summary="Daily summary",
    description="Get summary for a specific day: signings, worked hours, expected hours and overtime. If no date is specified, uses current day.",
)
class DaySummaryView(APIView):
    """Get summary for a specific day."""

    permission_classes = [IsAuthenticated]

    def get(self, request, day: str = None):
        if day:
            target_date = date.fromisoformat(day)
        else:
            target_date = date.today()

        user = request.user

        # Get work days (could be multiple for different locations)
        workdays = WorkDay.objects.filter(
            employee=user, date=target_date
        ).select_related("day_type", "location")

        # Get signings
        signings = Signing.objects.filter(
            employee=user,
            start_time__date=target_date,
        ).select_related("location")

        # Calculate totals
        total_worked_minutes = 0
        for signing in signings:
            if signing.duration_minutes:
                total_worked_minutes += signing.duration_minutes

        # Expected hours from all workdays
        total_expected_minutes = sum(
            int(wd.get_expected_hours() * 60) for wd in workdays
        )

        # If no workdays, use default 8 hours
        if not workdays.exists():
            total_expected_minutes = 480

        data = {
            "date": target_date,
            "workday": workdays.first(),  # For backward compatibility
            "signings": signings,
            "total_worked_minutes": total_worked_minutes,
            "expected_minutes": total_expected_minutes,
            "overtime_minutes": total_worked_minutes - total_expected_minutes,
        }

        serializer = DaySummarySerializer(data)
        return Response(serializer.data)


@extend_schema(
    tags=["Summaries"],
    summary="Period summary",
    description="Get summary of worked and overtime hours for a full month or year. Parameters: period (month/year), year, month.",
)
class PeriodSummaryView(APIView):
    """Get summary for a period (month/year)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get("period", "month")  # month or year
        year = int(request.query_params.get("year", date.today().year))
        month = int(request.query_params.get("month", date.today().month))

        user = request.user

        if period == "year":
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
        else:  # month
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)

        # Get all signings in period
        signings = Signing.objects.filter(
            employee=user,
            start_time__date__gte=start_date,
            start_time__date__lte=end_date,
        )

        # Calculate total worked
        total_worked_minutes = 0
        for signing in signings:
            if signing.duration_minutes:
                total_worked_minutes += signing.duration_minutes

        # Get work days to calculate expected
        workdays = WorkDay.objects.filter(
            employee=user,
            date__gte=start_date,
            date__lte=end_date,
        ).select_related("day_type", "location")

        total_expected_minutes = sum(
            int(wd.get_expected_hours() * 60) for wd in workdays
        )

        return Response({
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "total_worked_minutes": total_worked_minutes,
            "total_worked_hours": round(total_worked_minutes / 60, 2),
            "total_expected_minutes": total_expected_minutes,
            "total_expected_hours": round(total_expected_minutes / 60, 2),
            "overtime_minutes": total_worked_minutes - total_expected_minutes,
            "overtime_hours": round((total_worked_minutes - total_expected_minutes) / 60, 2),
            "days_worked": signings.values("start_time__date").distinct().count(),
        })


@extend_schema(
    tags=["Summaries"],
    summary="Range summary with weekly/monthly breakdown",
    description="Get summary of worked and overtime hours for a date range, with weekly and monthly breakdown.",
    parameters=[
        OpenApiParameter(
            name="start_date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Start date (YYYY-MM-DD)",
            required=True,
        ),
        OpenApiParameter(
            name="end_date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="End date (YYYY-MM-DD)",
            required=True,
        ),
    ],
)
class RangeSummaryView(APIView):
    """Get summary for a date range with weekly and monthly breakdown."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not start_date_str or not end_date_str:
            return Response(
                {"error": "Both start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if start_date > end_date:
            return Response(
                {"error": "start_date must be before or equal to end_date"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        # Get all signings in range
        signings = Signing.objects.filter(
            employee=user,
            start_time__date__gte=start_date,
            start_time__date__lte=end_date,
        )

        # Build map: date -> worked_minutes
        worked_by_date = defaultdict(int)
        for signing in signings:
            if signing.duration_minutes:
                signing_date = signing.start_time.date()
                worked_by_date[signing_date] += signing.duration_minutes

        # Get workdays in range
        workdays = WorkDay.objects.filter(
            employee=user,
            date__gte=start_date,
            date__lte=end_date,
        ).select_related("day_type", "location")

        # Build map: date -> expected_minutes
        expected_by_date = {}
        for wd in workdays:
            expected_by_date[wd.date] = int(wd.get_expected_hours() * 60)

        # For dates with signings but no workday, default to 480 min (8h)
        all_dates = set(worked_by_date.keys())
        for d in all_dates:
            if d not in expected_by_date:
                expected_by_date[d] = 480

        # Aggregate by month and week
        monthly = defaultdict(lambda: {"worked_minutes": 0, "expected_minutes": 0, "days": set()})
        weekly = defaultdict(lambda: {"worked_minutes": 0, "expected_minutes": 0, "days": set()})

        all_relevant_dates = set(worked_by_date.keys()) | set(expected_by_date.keys())

        for d in all_relevant_dates:
            worked = worked_by_date.get(d, 0)
            expected = expected_by_date.get(d, 0)

            # Monthly key
            month_key = (d.year, d.month)
            monthly[month_key]["worked_minutes"] += worked
            monthly[month_key]["expected_minutes"] += expected
            if worked > 0:
                monthly[month_key]["days"].add(d)

            # Weekly key (ISO week)
            iso = d.isocalendar()
            week_key = (iso[0], iso[1])
            weekly[week_key]["worked_minutes"] += worked
            weekly[week_key]["expected_minutes"] += expected
            if worked > 0:
                weekly[week_key]["days"].add(d)

        # Build response lists (descending order)
        monthly_list = sorted(
            [
                {
                    "year": k[0],
                    "month": k[1],
                    "worked_minutes": v["worked_minutes"],
                    "expected_minutes": v["expected_minutes"],
                    "overtime_minutes": v["worked_minutes"] - v["expected_minutes"],
                    "days_worked": len(v["days"]),
                }
                for k, v in monthly.items()
            ],
            key=lambda x: (x["year"], x["month"]),
            reverse=True,
        )

        weekly_list = sorted(
            [
                {
                    "year": k[0],
                    "week": k[1],
                    "worked_minutes": v["worked_minutes"],
                    "expected_minutes": v["expected_minutes"],
                    "overtime_minutes": v["worked_minutes"] - v["expected_minutes"],
                    "days_worked": len(v["days"]),
                }
                for k, v in weekly.items()
            ],
            key=lambda x: (x["year"], x["week"]),
            reverse=True,
        )

        total_worked = sum(worked_by_date.values())
        total_expected = sum(expected_by_date.values())

        return Response({
            "start_date": start_date,
            "end_date": end_date,
            "total_worked_minutes": total_worked,
            "total_expected_minutes": total_expected,
            "overtime_minutes": total_worked - total_expected,
            "days_worked": len(worked_by_date),
            "monthly": monthly_list,
            "weekly": weekly_list,
        })


@extend_schema(
    tags=["Import/Export"],
    summary="Import signings from CSV",
    description="""Import signings from a CSV file.

**CSV Format:**
```csv
start_time,end_time,location_id,description
2026-02-01 09:00,2026-02-01 18:00,1,Work at office
2026-02-02 08:30,2026-02-02 17:30,1,
```

**Fields:**
- `start_time` (required): Start datetime in format `YYYY-MM-DD HH:MM` or ISO8601
- `end_time` (optional): End datetime in same format
- `location_id` (optional): ID of the location
- `description` (optional): Text description

**Behavior:**
- Import is atomic: if any row fails, nothing is imported
- WorkDay records are automatically created for each signing
""",
)
class ImportSigningsView(APIView):
    """Import signings from a CSV file."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"error": "No file provided. Use 'file' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        csv_file = request.FILES["file"]

        # Read and decode the file
        try:
            decoded_file = csv_file.read().decode("utf-8")
        except UnicodeDecodeError:
            return Response(
                {"error": "File must be UTF-8 encoded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reader = csv.DictReader(io.StringIO(decoded_file))

        # Validate headers
        required_fields = {"start_time"}
        if not required_fields.issubset(set(reader.fieldnames or [])):
            return Response(
                {"error": f"CSV must contain columns: {', '.join(required_fields)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        errors = []
        signings_to_create = []
        row_num = 1  # Start at 1 (after header)

        for row in reader:
            row_num += 1
            row_errors = self._validate_row(row, row_num, request.user)

            if row_errors:
                errors.extend(row_errors)
            else:
                signing_data = self._parse_row(row, request.user)
                signings_to_create.append(signing_data)

        if errors:
            return Response({"imported": 0, "errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        # Create all signings in a transaction
        try:
            with transaction.atomic():
                imported_count = 0
                for data in signings_to_create:
                    signing = Signing.objects.create(
                        employee=request.user,
                        start_time=data["start_time"],
                        end_time=data.get("end_time"),
                        location=data.get("location"),
                        description=data.get("description", ""),
                    )

                    # Auto-create WorkDay
                    if signing.location:
                        signing_date = signing.start_time.date()
                        workday, _ = WorkDay.objects.get_or_create(
                            date=signing_date,
                            employee=request.user,
                            location=signing.location,
                            defaults={
                                "day_type": DayType.objects.get_or_create(
                                    name="Working", defaults={"requires_signing": True}
                                )[0]
                            },
                        )
                        signing.workday = workday
                        signing.save(update_fields=["workday"])

                    imported_count += 1

        except Exception as e:
            return Response(
                {"imported": 0, "errors": [{"row": 0, "error": str(e)}]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"imported": imported_count, "errors": []})

    def _validate_row(self, row, row_num, user):
        """Validate a single CSV row. Returns list of errors."""
        errors = []

        # Validate start_time
        start_time_str = row.get("start_time", "").strip()
        if not start_time_str:
            errors.append({"row": row_num, "error": "start_time is required"})
        else:
            try:
                self._parse_datetime(start_time_str)
            except ValueError:
                errors.append({"row": row_num, "error": "Invalid date format in start_time"})

        # Validate end_time if provided
        end_time_str = row.get("end_time", "").strip()
        if end_time_str:
            try:
                self._parse_datetime(end_time_str)
            except ValueError:
                errors.append({"row": row_num, "error": "Invalid date format in end_time"})

        # Validate location_id if provided
        location_id_str = row.get("location_id", "").strip()
        if location_id_str:
            try:
                location_id = int(location_id_str)
                if not Location.objects.filter(id=location_id).exists():
                    errors.append({"row": row_num, "error": f"Location with id {location_id} not found"})
            except ValueError:
                errors.append({"row": row_num, "error": "location_id must be a number"})

        return errors

    def _parse_row(self, row, user):
        """Parse a validated CSV row into signing data."""
        data = {
            "start_time": self._parse_datetime(row["start_time"].strip()),
            "description": row.get("description", "").strip(),
        }

        end_time_str = row.get("end_time", "").strip()
        if end_time_str:
            data["end_time"] = self._parse_datetime(end_time_str)

        location_id_str = row.get("location_id", "").strip()
        if location_id_str:
            data["location"] = Location.objects.get(id=int(location_id_str))

        return data

    def _parse_datetime(self, dt_str):
        """Parse datetime string in YYYY-MM-DD HH:MM or ISO8601 format."""
        # Try simple format first
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"]:
            try:
                return timezone.make_aware(datetime.strptime(dt_str, fmt))
            except ValueError:
                continue

        # Try ISO format with timezone
        try:
            return datetime.fromisoformat(dt_str)
        except ValueError:
            pass

        raise ValueError(f"Cannot parse datetime: {dt_str}")


@extend_schema(
    tags=["Import/Export"],
    summary="Export signings to CSV",
    description="""Export signings to a CSV file.

**Query Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

**Response:**
Returns a CSV file with columns: date, start_time, end_time, duration_minutes, location, description
""",
    parameters=[
        OpenApiParameter(
            name="start_date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Start date (YYYY-MM-DD)",
            required=True,
        ),
        OpenApiParameter(
            name="end_date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="End date (YYYY-MM-DD)",
            required=True,
        ),
    ],
)
class ExportSigningsView(APIView):
    """Export signings to a CSV file."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not start_date_str or not end_date_str:
            return Response(
                {"error": "Both start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if start_date > end_date:
            return Response(
                {"error": "start_date must be before or equal to end_date"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get signings in the date range
        signings = Signing.objects.filter(
            employee=request.user,
            start_time__date__gte=start_date,
            start_time__date__lte=end_date,
        ).select_related("location").order_by("start_time")

        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="signings_{start_date}_{end_date}.csv"'

        writer = csv.writer(response)
        writer.writerow(["date", "start_time", "end_time", "duration_minutes", "location", "description"])

        for signing in signings:
            writer.writerow([
                signing.start_time.date(),
                signing.start_time,
                signing.end_time if signing.end_time else "",
                signing.duration_minutes if signing.duration_minutes else "",
                signing.location.name if signing.location else "",
                signing.description,
            ])

        return response
