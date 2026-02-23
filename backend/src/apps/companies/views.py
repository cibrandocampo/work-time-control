from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import BankHoliday, Company, Location
from .serializers import BankHolidaySerializer, CompanySerializer, LocationSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Companies"],
        summary="List companies",
        description="Get all companies in the system.",
    ),
    create=extend_schema(
        tags=["Companies"],
        summary="Create company",
        description="Create a new company with default daily hours configuration.",
    ),
    retrieve=extend_schema(
        tags=["Companies"],
        summary="Get company",
        description="Get details of a specific company.",
    ),
    update=extend_schema(
        tags=["Companies"],
        summary="Update company",
        description="Fully update an existing company.",
    ),
    partial_update=extend_schema(
        tags=["Companies"],
        summary="Partial update company",
        description="Update one or more fields of a company.",
    ),
    destroy=extend_schema(
        tags=["Companies"],
        summary="Delete company",
        description="Delete a company and all associated data.",
    ),
)
class CompanyViewSet(viewsets.ModelViewSet):
    """Company management."""
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(
        tags=["Locations"],
        summary="List locations",
        description="Get all locations for the user's companies.",
    ),
    create=extend_schema(
        tags=["Locations"],
        summary="Create location",
        description="Create a new company location with work schedule defaults and address.",
    ),
    retrieve=extend_schema(
        tags=["Locations"],
        summary="Get location",
        description="Get details of a specific location.",
    ),
    update=extend_schema(
        tags=["Locations"],
        summary="Update location",
        description="Fully update an existing location.",
    ),
    partial_update=extend_schema(
        tags=["Locations"],
        summary="Partial update location",
        description="Update one or more fields of a location.",
    ),
    destroy=extend_schema(
        tags=["Locations"],
        summary="Delete location",
        description="Delete a location. Users assigned to this location will be unlinked.",
    ),
)
class LocationViewSet(viewsets.ModelViewSet):
    """Company location management."""
    queryset = Location.objects.select_related("company").all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter locations by user's companies."""
        user = self.request.user
        user_companies = user.locations.values_list("company_id", flat=True)
        if user_companies:
            return self.queryset.filter(company_id__in=user_companies)
        return self.queryset.none()


@extend_schema_view(
    list=extend_schema(
        tags=["Bank Holidays"],
        summary="List bank holidays",
        description="Get all bank holidays for the user's location (national, regional and local).",
    ),
    create=extend_schema(
        tags=["Bank Holidays"],
        summary="Create bank holiday",
        description="Add a new bank holiday to a location's calendar.",
    ),
    retrieve=extend_schema(
        tags=["Bank Holidays"],
        summary="Get bank holiday",
        description="Get details of a specific bank holiday.",
    ),
    update=extend_schema(
        tags=["Bank Holidays"],
        summary="Update bank holiday",
        description="Fully update an existing bank holiday.",
    ),
    partial_update=extend_schema(
        tags=["Bank Holidays"],
        summary="Partial update bank holiday",
        description="Update one or more fields of a bank holiday.",
    ),
    destroy=extend_schema(
        tags=["Bank Holidays"],
        summary="Delete bank holiday",
        description="Remove a bank holiday from a location's calendar.",
    ),
)
class BankHolidayViewSet(viewsets.ModelViewSet):
    """Bank holiday calendar management."""
    queryset = BankHoliday.objects.select_related("location").all()
    serializer_class = BankHolidaySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter holidays by user's locations."""
        user = self.request.user
        user_locations = user.locations.values_list("id", flat=True)
        if user_locations:
            return self.queryset.filter(location_id__in=user_locations)
        return self.queryset.none()
