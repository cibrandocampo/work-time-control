from rest_framework import serializers

from .models import DayType


class DayTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DayType
        fields = ["id", "name", "requires_signing"]
