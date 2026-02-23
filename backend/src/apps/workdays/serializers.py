from rest_framework import serializers

from .models import Signing, WorkDay


class WorkDaySerializer(serializers.ModelSerializer):
    day_type_name = serializers.CharField(source="day_type.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    expected_hours_calculated = serializers.SerializerMethodField()

    class Meta:
        model = WorkDay
        fields = [
            "id",
            "date",
            "employee",
            "location",
            "location_name",
            "day_type",
            "day_type_name",
            "expected_hours",
            "expected_hours_calculated",
            "note",
        ]
        read_only_fields = ["id", "employee"]

    def get_expected_hours_calculated(self, obj):
        return obj.get_expected_hours()


class SigningSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source="location.name", read_only=True)
    duration = serializers.FloatField(read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Signing
        fields = [
            "id",
            "employee",
            "workday",
            "start_time",
            "end_time",
            "location",
            "location_name",
            "latitude_start",
            "longitude_start",
            "latitude_end",
            "longitude_end",
            "description",
            "duration",
            "duration_minutes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "employee", "created_at", "updated_at"]


class SigningCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new signing (check-in)."""

    class Meta:
        model = Signing
        fields = [
            "start_time",
            "location",
            "latitude_start",
            "longitude_start",
            "description",
        ]


class SigningUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a signing (check-out)."""

    class Meta:
        model = Signing
        fields = [
            "end_time",
            "latitude_end",
            "longitude_end",
            "description",
        ]


class DaySummarySerializer(serializers.Serializer):
    """Summary of a day's signings."""

    date = serializers.DateField()
    workday = WorkDaySerializer(allow_null=True)
    signings = SigningSerializer(many=True)
    total_worked_minutes = serializers.IntegerField()
    expected_minutes = serializers.IntegerField()
    overtime_minutes = serializers.IntegerField()
