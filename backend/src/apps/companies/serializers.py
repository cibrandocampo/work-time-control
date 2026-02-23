from rest_framework import serializers

from .models import BankHoliday, Company, Location


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name"]


class LocationSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Location
        fields = [
            "id",
            "company",
            "company_name",
            "name",
            "default_daily_hours",
            "default_rest_days",
            "address",
            "city",
            "country",
            "latitude",
            "longitude",
        ]


class BankHolidaySerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source="location.name", read_only=True)

    class Meta:
        model = BankHoliday
        fields = ["id", "location", "location_name", "date", "name"]
