from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import DayType
from .serializers import DayTypeSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Day Types"],
        summary="List day types",
        description="Get all available day types (Working, Vacation, Sick Leave, Holiday, etc.).",
    ),
    create=extend_schema(
        tags=["Day Types"],
        summary="Create day type",
        description="Create a new day type with signing requirements.",
    ),
    retrieve=extend_schema(
        tags=["Day Types"],
        summary="Get day type",
        description="Get details of a specific day type.",
    ),
    update=extend_schema(
        tags=["Day Types"],
        summary="Update day type",
        description="Fully update an existing day type.",
    ),
    partial_update=extend_schema(
        tags=["Day Types"],
        summary="Partial update day type",
        description="Update one or more fields of a day type.",
    ),
    destroy=extend_schema(
        tags=["Day Types"],
        summary="Delete day type",
        description="Delete a day type. Work days using this type will be affected.",
    ),
)
class DayTypeViewSet(viewsets.ModelViewSet):
    """Day type catalog management."""
    queryset = DayType.objects.all()
    serializer_class = DayTypeSerializer
    permission_classes = [IsAuthenticated]
